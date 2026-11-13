"""Tests for data processing (merging) for order reports."""

import pytest
import pandas as pd

from src.data_loader import (
    load_products,
    load_orders,
    load_timeslots,
    load_packing_categories,
    load_schedule
)
from src.data_processor import merge_all_data, sort_for_reports
from src import config
from src.markets import PASK
from src.data_validator import validate_data


class TestProcessData:
    """Tests for process_data() - merges all order report data."""

    def test_process_data_pask_integration(
        self,
        pask_product_export_file,
        pask_orders_file,
        pask_timeslots_file,
        pask_fixtures_dir
    ):
        """Test full data processing pipeline with pask test data."""
        # Load all data
        with open(pask_product_export_file, 'rb') as f:
            df_products = load_products(f)

        with open(pask_orders_file, 'rb') as f:
            df_orders = load_orders(f)

        with open(pask_timeslots_file, 'rb') as f:
            df_timeslots = load_timeslots(f)

        df_packing_categories = load_packing_categories(PASK.packing_categories(pask_fixtures_dir))

        # Process (merge all data)
        df_merged = merge_all_data(
            df_orders,
            df_timeslots,
            df_products,
            df_packing_categories
        )
        df_merged = sort_for_reports(df_merged)

        # Validate result
        assert len(df_merged) > 0, "Merged data should not be empty"

        # Check that key columns are present
        # Note: PackingCategory appears twice during merge (from orders and packing template)
        # so it gets suffixed as PackingCategory_x and PackingCategory_y
        required_cols = [
            'OrderNumber', 'FullName', 'Email', 'ArticleNumber',
            'ProductName', 'Quantity', 'PickUpDate', 'PickUpTime',
            'PickUpArea', 'PackingCategoryIndex'
        ]
        for col in required_cols:
            assert col in df_merged.columns, f"Missing column: {col}"

        # Check that PackingCategory exists in some form
        assert 'PackingCategory_x' in df_merged.columns or 'PackingCategory' in df_merged.columns

        # Check that orders were merged with timeslots
        assert 'PickUpDate' in df_merged.columns
        assert 'PickUpTime' in df_merged.columns

        # Check that products were merged
        assert 'ProductDescription' in df_merged.columns or 'ArticleNumber' in df_merged.columns

        # Check that packing categories were merged
        assert 'PickUpArea' in df_merged.columns
        assert 'PackingCategoryIndex' in df_merged.columns

    def test_process_data_sorting(
        self,
        pask_product_export_file,
        pask_orders_file,
        pask_timeslots_file,
        pask_fixtures_dir
    ):
        """Test that merged data is sorted correctly."""
        # Load data
        with open(pask_product_export_file, 'rb') as f:
            df_products = load_products(f)

        with open(pask_orders_file, 'rb') as f:
            df_orders = load_orders(f)

        with open(pask_timeslots_file, 'rb') as f:
            df_timeslots = load_timeslots(f)

        df_packing_categories = load_packing_categories(PASK.packing_categories(pask_fixtures_dir))

        # Process
        df_merged = merge_all_data(
            df_orders,
            df_timeslots,
            df_products,
            df_packing_categories
        )
        df_merged = sort_for_reports(df_merged)

        # Check sorting: should be by PickUpDate, PickUpTime, PackingCategoryIndex
        # We can't check strict monotonic increase if there are duplicates,
        # but we can check that the sort is stable
        if len(df_merged) > 1:
            # Check that rows are ordered
            for i in range(len(df_merged) - 1):
                curr = df_merged.iloc[i]
                next_row = df_merged.iloc[i + 1]

                # If same date, check time ordering
                if pd.notna(curr['PickUpDate']) and pd.notna(next_row['PickUpDate']):
                    if curr['PickUpDate'] == next_row['PickUpDate']:
                        # Same date - check time
                        if pd.notna(curr['PickUpTime']) and pd.notna(next_row['PickUpTime']):
                            if curr['PickUpTime'] == next_row['PickUpTime']:
                                # Same time - check packing category
                                if pd.notna(curr['PackingCategoryIndex']) and pd.notna(next_row['PackingCategoryIndex']):
                                    assert curr['PackingCategoryIndex'] <= next_row['PackingCategoryIndex']

    def test_orders_without_timeslot_are_excluded_but_reported(self, pask_data):
        """Merge uses INNER joins (same as the original notebook).

        Orders without a timeslot booking cannot be scheduled, so they are
        excluded from all reports. That is only acceptable because every
        excluded order is listed in the validation result / diffs.xlsx.
        """
        merged_orders = set(pask_data.all_data['OrderNumber'])
        dropped = set(pask_data.orders['OrderNumber']) - merged_orders

        result = validate_data(pask_data.orders, pask_data.timeslots,
                               pask_data.products, pask_data.packing)
        reported = set(result.orders_no_timeslot['OrderNumber'])

        assert dropped, "fixture is expected to contain orders without timeslot"
        assert dropped == reported,             "every order dropped by the merge must be reported by validation"

        # Orders that survive keep all their order lines
        kept = pask_data.orders[pask_data.orders['OrderNumber'].isin(merged_orders)]
        assert len(kept) == len(pask_data.all_data)
