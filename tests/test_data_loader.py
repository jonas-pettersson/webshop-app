"""Tests for data loading functions."""

import pytest
import pandas as pd
from pathlib import Path

from src.data_loader import (
    load_products,
    load_orders,
    load_timeslots,
    load_packing_categories,
    load_schedule,
    load_product_export,
    load_products_report_export,
    load_sku_mapping
)
from src import config


class TestLoadProducts:
    """Tests for load_products() - used by order reports."""

    def test_load_products_pask(self, pask_product_export_file):
        """Test loading products from pask product export."""
        with open(pask_product_export_file, 'rb') as f:
            df = load_products(f)

        # Check columns
        assert list(df.columns) == ['ArticleNumber', 'ProductDescription', 'RegularPrice']

        # Check data loaded
        assert len(df) > 0

        # Check SKU format
        assert df['ArticleNumber'].notna().all()


class TestLoadOrders:
    """Tests for load_orders() - used by order reports."""

    def test_load_orders_pask(self, pask_orders_file):
        """Test loading orders from pask orders export."""
        with open(pask_orders_file, 'rb') as f:
            df = load_orders(f)

        # Check expected columns
        expected_cols = [
            'OrderNumber', 'FullName', 'Email', 'OrderTotalAmount',
            'OrderDate', 'CustomerNote', 'PhoneOrder', 'ArticleNumber',
            'Quantity', 'ProductName', 'ItemCost', 'ItemID', 'Info',
            'PackingCategory', 'PackingCategoryKey'
        ]
        assert list(df.columns) == expected_cols

        # Check data loaded
        assert len(df) > 0

        # Check email normalization (should be lowercase)
        assert df['Email'].str.islower().all()

        # Check PackingCategoryKey created
        assert df['PackingCategoryKey'].notna().all()


class TestLoadTimeslots:
    """Tests for load_timeslots() - used by order reports."""

    def test_load_timeslots_pask(self, pask_timeslots_file):
        """Test loading timeslots from pask booking export."""
        with open(pask_timeslots_file, 'rb') as f:
            df = load_timeslots(f, market_type=config.MARKET_TYPE_PASK)

        # Check expected columns
        expected_cols = [
            'OrderTime', 'Email', 'PickUpDate', 'PickUpTime',
            'PickUpDateTime', 'FullNameTimeslot', 'Telephone'
        ]
        assert list(df.columns) == expected_cols

        # Check data loaded
        assert len(df) > 0

        # Check email normalization (should be lowercase)
        assert df['Email'].str.islower().all()

        # Check PickUpTime is time type
        assert pd.api.types.is_object_dtype(df['PickUpTime'])


class TestLoadPackingCategories:
    """Tests for load_packing_categories() - used by order reports."""

    def test_load_packing_categories_pask(self, pask_packing_categories_file, pask_fixtures_dir):
        """Test loading packing categories from template."""
        df = load_packing_categories(
            market_type=config.MARKET_TYPE_PASK,
            template_dir=pask_fixtures_dir
        )

        # Check expected columns
        expected_cols = [
            'PickUpArea', 'PackingCategory', 'PackingCategoryKey',
            'PackingCategoryIndex'
        ]
        assert list(df.columns) == expected_cols

        # Check data loaded
        assert len(df) > 0

        # Check PackingCategoryKey created (lowercase)
        assert df['PackingCategoryKey'].str.islower().all()

        # Check index created
        assert df['PackingCategoryIndex'].notna().all()


class TestLoadSchedule:
    """Tests for load_schedule() - used by order reports."""

    def test_load_schedule_pask(self, pask_schedule_file, pask_fixtures_dir):
        """Test loading schedule from template."""
        df = load_schedule(
            market_type=config.MARKET_TYPE_PASK,
            template_dir=pask_fixtures_dir
        )

        # Check expected columns
        expected_cols = ['Dag', 'Tid', 'Date', 'DateTime']
        assert list(df.columns) == expected_cols

        # Check data loaded
        assert len(df) > 0

        # Check Date and DateTime columns created
        assert df['Date'].notna().all()
        assert df['DateTime'].notna().all()


class TestLoadProductExport:
    """Tests for load_product_export() - used by inventory reports."""

    def test_load_product_export_pask(self, pask_product_export_file):
        """Test loading product export for inventory report."""
        with open(pask_product_export_file, 'rb') as f:
            df = load_product_export(f)

        # Check expected columns (order may vary)
        expected_cols = ['SKU', 'Name', 'Regular price', 'Stock', 'Tax status', 'Tax class']
        assert set(df.columns) == set(expected_cols)

        # Check data loaded
        assert len(df) > 0

        # Check SKU stripped
        assert not df['SKU'].str.contains(' $', regex=True).any()

        # Check Regular price converted to numeric
        assert pd.api.types.is_numeric_dtype(df['Regular price'])

        # Check that prices are valid numbers (not NaN for products with prices)
        products_with_price = df[df['Regular price'].notna()]
        if len(products_with_price) > 0:
            assert (products_with_price['Regular price'] >= 0).all()

    def test_decimal_notation_handling(self, tmp_path):
        """Test that both English (dot) and German (comma) decimal notation work."""
        # Create test CSV with German notation (commas)
        test_csv = tmp_path / "test_german.csv"
        test_csv.write_text(
            'SKU,Name,Regular price,Stock,Tax status,Tax class\n'
            '#TEST1#,Product 1,"12,50",10,taxable,standard\n'
            '#TEST2#,Product 2,"5,99",5,taxable,reduced\n'
        )

        # Load with German notation
        with open(test_csv, 'rb') as f:
            df = load_product_export(f)

        # Check prices parsed correctly
        assert df.loc[df['SKU'] == '#TEST1#', 'Regular price'].iloc[0] == 12.50
        assert df.loc[df['SKU'] == '#TEST2#', 'Regular price'].iloc[0] == 5.99

        # Create test CSV with English notation (dots)
        test_csv_en = tmp_path / "test_english.csv"
        test_csv_en.write_text(
            'SKU,Name,Regular price,Stock,Tax status,Tax class\n'
            '#TEST1#,Product 1,12.50,10,taxable,standard\n'
            '#TEST2#,Product 2,5.99,5,taxable,reduced\n'
        )

        # Load with English notation
        with open(test_csv_en, 'rb') as f:
            df = load_product_export(f)

        # Check prices parsed correctly
        assert df.loc[df['SKU'] == '#TEST1#', 'Regular price'].iloc[0] == 12.50
        assert df.loc[df['SKU'] == '#TEST2#', 'Regular price'].iloc[0] == 5.99


class TestLoadProductsReportExport:
    """Tests for load_products_report_export() - used by inventory reports."""

    def test_load_products_report_pask(self, pask_products_report_file):
        """Test loading products report for inventory."""
        with open(pask_products_report_file, 'rb') as f:
            df = load_products_report_export(f)

        # Check expected columns
        expected_cols = ['Product title', 'SKU', 'Items sold', 'N. Revenue', 'Category', 'Stock']
        assert list(df.columns) == expected_cols

        # Check data loaded
        assert len(df) > 0

        # Check SKU stripped
        assert not df['SKU'].str.contains(' $', regex=True).any()

        # Check Items sold converted to numeric
        assert pd.api.types.is_numeric_dtype(df['Items sold'])

        # Check that quantities are valid (>= 0)
        items_sold = df[df['Items sold'].notna()]
        if len(items_sold) > 0:
            assert (items_sold['Items sold'] >= 0).all()

    def test_decimal_notation_handling_items_sold(self, tmp_path):
        """Test that both English and German notation work for Items sold."""
        # Create test CSV with German notation (commas) - edge case
        test_csv = tmp_path / "test_german_items.csv"
        test_csv.write_text(
            'Product title,SKU,Items sold,N. Revenue,Category,Stock\n'
            'Product 1,#TEST1#,"100,5",1000,Cat1,10\n'
            'Product 2,#TEST2#,"50,0",500,Cat2,5\n'
        )

        # Load with German notation
        with open(test_csv, 'rb') as f:
            df = load_products_report_export(f)

        # Check items parsed correctly
        assert df.loc[df['SKU'] == '#TEST1#', 'Items sold'].iloc[0] == 100.5
        assert df.loc[df['SKU'] == '#TEST2#', 'Items sold'].iloc[0] == 50.0
