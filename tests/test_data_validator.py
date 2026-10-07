"""Tests for data validation functions."""

import pytest
import pandas as pd

from src.data_loader import (
    load_products,
    load_orders,
    load_timeslots,
    load_packing_categories
)
from src.data_validator import (
    validate_data,
    remove_duplicate_bookings,
    validate_inventory_data
)
from src import config


class TestValidateData:
    """Tests for validate_data() - validates order report data."""

    def test_validate_data_pask(
        self,
        pask_product_export_file,
        pask_orders_file,
        pask_timeslots_file,
        pask_fixtures_dir
    ):
        """Test data validation with pask test data."""
        # Load data
        with open(pask_product_export_file, 'rb') as f:
            df_products = load_products(f)

        with open(pask_orders_file, 'rb') as f:
            df_orders = load_orders(f)

        with open(pask_timeslots_file, 'rb') as f:
            df_timeslots = load_timeslots(f, market_type=config.MARKET_TYPE_PASK)

        df_packing_categories = load_packing_categories(
            market_type=config.MARKET_TYPE_PASK,
            template_dir=pask_fixtures_dir
        )

        # Validate
        validation_results = validate_data(
            df_orders,
            df_timeslots,
            df_products,
            df_packing_categories
        )

        # Check that validation results structure is correct
        assert isinstance(validation_results, dict)
        assert 'orders_without_timeslots' in validation_results
        assert 'timeslots_without_orders' in validation_results
        assert 'duplicate_bookings' in validation_results
        assert 'missing_products' in validation_results
        assert 'missing_packing_categories' in validation_results

        # Each result should be a DataFrame
        for key, value in validation_results.items():
            assert isinstance(value, pd.DataFrame), f"{key} should be a DataFrame"

    def test_validate_data_reports_issues(
        self,
        pask_product_export_file,
        pask_orders_file,
        pask_timeslots_file,
        pask_fixtures_dir
    ):
        """Test that validation catches real issues in data."""
        # Load data
        with open(pask_product_export_file, 'rb') as f:
            df_products = load_products(f)

        with open(pask_orders_file, 'rb') as f:
            df_orders = load_orders(f)

        with open(pask_timeslots_file, 'rb') as f:
            df_timeslots = load_timeslots(f, market_type=config.MARKET_TYPE_PASK)

        df_packing_categories = load_packing_categories(
            market_type=config.MARKET_TYPE_PASK,
            template_dir=pask_fixtures_dir
        )

        # Validate
        validation_results = validate_data(
            df_orders,
            df_timeslots,
            df_products,
            df_packing_categories
        )

        # Report validation summary
        total_issues = sum(len(df) for df in validation_results.values())
        print(f"\nValidation Summary for pask test data:")
        print(f"  Orders without timeslots: {len(validation_results['orders_without_timeslots'])}")
        print(f"  Timeslots without orders: {len(validation_results['timeslots_without_orders'])}")
        print(f"  Duplicate bookings: {len(validation_results['duplicate_bookings'])}")
        print(f"  Missing products: {len(validation_results['missing_products'])}")
        print(f"  Missing packing categories: {len(validation_results['missing_packing_categories'])}")
        print(f"  Total issues: {total_issues}")


class TestRemoveDuplicateBookings:
    """Tests for remove_duplicate_bookings()."""

    def test_remove_duplicate_bookings_keeps_first(self):
        """Test that duplicate bookings are removed, keeping first occurrence."""
        # Create test data with duplicates
        df_timeslots = pd.DataFrame({
            'Email': ['test@example.com', 'test@example.com', 'other@example.com'],
            'PickUpDate': [
                pd.Timestamp('2025-03-20'),
                pd.Timestamp('2025-03-20'),
                pd.Timestamp('2025-03-20')
            ],
            'PickUpTime': ['10:00', '11:00', '10:00'],
            'OrderTime': [
                pd.Timestamp('2025-03-01 08:00'),
                pd.Timestamp('2025-03-01 09:00'),
                pd.Timestamp('2025-03-01 10:00')
            ]
        })

        # Remove duplicates
        df_cleaned = remove_duplicate_bookings(df_timeslots)

        # Should keep only first booking for test@example.com (at 10:00)
        test_bookings = df_cleaned[df_cleaned['Email'] == 'test@example.com']
        assert len(test_bookings) == 1
        assert test_bookings.iloc[0]['PickUpTime'] == '10:00'

        # Should keep other@example.com
        other_bookings = df_cleaned[df_cleaned['Email'] == 'other@example.com']
        assert len(other_bookings) == 1

    def test_remove_duplicate_bookings_no_duplicates(self):
        """Test that data without duplicates is unchanged."""
        # Create test data without duplicates
        df_timeslots = pd.DataFrame({
            'Email': ['test1@example.com', 'test2@example.com', 'test3@example.com'],
            'PickUpDate': [
                pd.Timestamp('2025-03-20'),
                pd.Timestamp('2025-03-20'),
                pd.Timestamp('2025-03-21')
            ],
            'PickUpTime': ['10:00', '11:00', '10:00']
        })

        # Remove duplicates
        df_cleaned = remove_duplicate_bookings(df_timeslots)

        # Should have same length
        assert len(df_cleaned) == len(df_timeslots)


class TestValidateInventoryData:
    """Tests for validate_inventory_data()."""

    def test_validate_inventory_data_pask(
        self,
        pask_product_export_file,
        pask_products_report_file
    ):
        """Test inventory data validation with pask test data."""
        # Load data
        from src.data_loader import load_product_export, load_products_report_export

        with open(pask_product_export_file, 'rb') as f:
            df_product_export = load_product_export(f)

        with open(pask_products_report_file, 'rb') as f:
            df_products_report = load_products_report_export(f)

        # Validate
        validation_results = validate_inventory_data(
            df_product_export,
            df_products_report
        )

        # Check structure
        assert isinstance(validation_results, dict)
        assert 'products_with_sales_but_no_price' in validation_results
        assert 'products_in_report_not_in_catalog' in validation_results

        # Each result should be a DataFrame
        for key, value in validation_results.items():
            assert isinstance(value, pd.DataFrame), f"{key} should be a DataFrame"

        # Report validation summary
        print(f"\nInventory Validation Summary for pask:")
        print(f"  Products with sales but no price: {len(validation_results['products_with_sales_but_no_price'])}")
        print(f"  Products in report not in catalog: {len(validation_results['products_in_report_not_in_catalog'])}")

    def test_validate_inventory_detects_missing_prices(self):
        """Test that validation detects products with sales but no price."""
        # Create test data
        df_product_export = pd.DataFrame({
            'SKU': ['#TEST1#', '#TEST2#', '#TEST3#'],
            'Regular price': [10.50, None, 15.99]  # TEST2 has no price
        })

        df_products_report = pd.DataFrame({
            'SKU': ['#TEST1#', '#TEST2#', '#TEST3#'],
            'Items sold': [10, 5, 20]  # TEST2 has sales but no price
        })

        # Validate
        validation_results = validate_inventory_data(
            df_product_export,
            df_products_report
        )

        # Should detect TEST2 as having sales but no price
        missing_prices = validation_results['products_with_sales_but_no_price']
        assert len(missing_prices) == 1
        assert missing_prices.iloc[0]['SKU'] == '#TEST2#'
