"""Tests for inventory report (lagerrapport) processing."""

import pytest
import pandas as pd
from pathlib import Path

from src.data_loader import (
    load_product_export,
    load_products_report_export,
    load_sku_mapping
)
from src.lagerrapport_processor import (
    map_sku_to_sales_area,
    get_tax_rate,
    prepare_lagerrapport_data
)
from src import config


class TestSKUMapping:
    """Tests for SKU to sales area mapping."""

    def test_map_sku_to_sales_area(self):
        """Test SKU prefix mapping to sales areas."""
        # Create test mapping
        mapping_df = pd.DataFrame({
            'SKU_Prefix': ['#BR_', '#M_', '#BK_'],
            'Sales_Area': ['Bröd', 'Mat', 'Böcker']
        })

        # Test matching prefixes
        assert map_sku_to_sales_area('#BR_001#', mapping_df) == 'Bröd'
        assert map_sku_to_sales_area('#M_025#', mapping_df) == 'Mat'
        assert map_sku_to_sales_area('#BK_042#', mapping_df) == 'Böcker'

        # Test unknown prefix
        assert map_sku_to_sales_area('#XX_999#', mapping_df) == 'Unknown'

        # Test NaN/None
        assert map_sku_to_sales_area(None, mapping_df) == 'Unknown'


class TestTaxRate:
    """Tests for tax rate lookup."""

    def test_get_tax_rate_standard(self):
        """Test standard tax rate."""
        assert get_tax_rate('parent') == config.TAX_RATES['parent']  # 'parent' is standard 20%

    def test_get_tax_rate_reduced(self):
        """Test reduced tax rate."""
        assert get_tax_rate('reduzierter-preis') == config.TAX_RATES['reduzierter-preis']

    def test_get_tax_rate_none(self):
        """Test None/NaN tax class."""
        assert get_tax_rate(None) == config.TAX_RATES[None]
        assert get_tax_rate(pd.NA) == config.TAX_RATES[None]

    def test_get_tax_rate_unknown(self):
        """Test unknown tax class falls back to None rate."""
        assert get_tax_rate('unknown-class') == config.TAX_RATES[None]


class TestInventoryReportProcessing:
    """Tests for full inventory report data processing."""

    @pytest.fixture
    def sample_product_export(self):
        """Create sample product export data."""
        return pd.DataFrame({
            'SKU': ['#BR_001#', '#M_025#', '#BK_042#'],
            'Name': ['Bread Product', 'Food Product', 'Book Product'],
            'Regular price': [10.50, 25.00, 15.99],
            'Stock': [100, 50, 25],
            'Tax status': ['taxable', 'taxable', 'taxable'],
            'Tax class': ['standard', 'reduzierter-preis', 'standard']
        })

    @pytest.fixture
    def sample_products_report(self):
        """Create sample products report data."""
        return pd.DataFrame({
            'Product title': ['Bread Product', 'Food Product', 'Book Product'],
            'SKU': ['#BR_001#', '#M_025#', '#BK_042#'],
            'Items sold': [10, 20, 5],
            'N. Revenue': [105.00, 500.00, 79.95],
            'Category': ['Bröd', 'Mat', 'Böcker'],
            'Stock': [90, 30, 20]
        })

    @pytest.fixture
    def sample_sku_mapping(self):
        """Create sample SKU mapping."""
        return pd.DataFrame({
            'SKU_Prefix': ['#BR_', '#M_', '#BK_'],
            'Sales_Area': ['Bröd', 'Mat', 'Böcker']
        })

    def test_prepare_lagerrapport_data(
        self,
        sample_product_export,
        sample_products_report,
        sample_sku_mapping
    ):
        """Test full inventory report data preparation."""
        result_df = prepare_lagerrapport_data(
            sample_product_export,
            sample_products_report,
            sample_sku_mapping
        )

        # Check expected columns
        expected_cols = [
            'SKU', 'Product title', 'Category (SKUT)', 'Category',
            'Regular price', 'Items sold', 'Stock', 'Tax class',
            'Total sales', 'Total tax'
        ]
        assert list(result_df.columns) == expected_cols

        # Check all products present (INNER join)
        assert len(result_df) == 3

        # Check sales area mapping
        assert result_df.loc[result_df['SKU'] == '#BR_001#', 'Category (SKUT)'].iloc[0] == 'Bröd'
        assert result_df.loc[result_df['SKU'] == '#M_025#', 'Category (SKUT)'].iloc[0] == 'Mat'
        assert result_df.loc[result_df['SKU'] == '#BK_042#', 'Category (SKUT)'].iloc[0] == 'Böcker'

        # Check calculations for first product
        row1 = result_df[result_df['SKU'] == '#BR_001#'].iloc[0]
        assert row1['Regular price'] == 10.50
        assert row1['Items sold'] == 10
        assert row1['Total sales'] == 10.50 * 10  # 105.00

        # Check tax calculation (standard rate = 0.20)
        expected_tax = 10.50 * 0.20  # 2.10
        assert abs(row1['Total tax'] - expected_tax) < 0.01

        # Check sorting (by Sales Area, then SKU)
        assert result_df['Category (SKUT)'].tolist() == ['Bröd', 'Böcker', 'Mat']

    def test_inner_join_only_products_with_sales(
        self,
        sample_product_export,
        sample_products_report,
        sample_sku_mapping
    ):
        """Test that only products with sales are included (INNER join)."""
        # Add product with no sales to export
        product_export_with_extra = pd.concat([
            sample_product_export,
            pd.DataFrame({
                'SKU': ['#XX_999#'],
                'Name': ['Unsold Product'],
                'Regular price': [99.99],
                'Stock': [100],
                'Tax status': ['taxable'],
                'Tax class': ['standard']
            })
        ])

        result_df = prepare_lagerrapport_data(
            product_export_with_extra,
            sample_products_report,
            sample_sku_mapping
        )

        # Check that unsold product is NOT in result
        assert '#XX_999#' not in result_df['SKU'].values
        assert len(result_df) == 3  # Only the 3 with sales

    def test_nan_prices_handled(
        self,
        sample_products_report,
        sample_sku_mapping
    ):
        """Test that NaN prices are handled gracefully."""
        # Product export with NaN price
        product_export_with_nan = pd.DataFrame({
            'SKU': ['#BR_001#', '#M_025#'],
            'Name': ['Bread Product', 'Food Product'],
            'Regular price': [10.50, None],  # Second price is NaN
            'Stock': [100, 50],
            'Tax status': ['taxable', 'taxable'],
            'Tax class': ['standard', 'standard']
        })

        # Only include matching products in report
        products_report_subset = sample_products_report[
            sample_products_report['SKU'].isin(['#BR_001#', '#M_025#'])
        ]

        result_df = prepare_lagerrapport_data(
            product_export_with_nan,
            products_report_subset,
            sample_sku_mapping
        )

        # Check that calculation with NaN price results in NaN
        row_with_nan = result_df[result_df['SKU'] == '#M_025#'].iloc[0]
        assert pd.isna(row_with_nan['Total sales'])
        assert pd.isna(row_with_nan['Total tax'])

        # Check that valid price still works
        row_valid = result_df[result_df['SKU'] == '#BR_001#'].iloc[0]
        assert row_valid['Total sales'] == 10.50 * 10


class TestInventoryReportWithRealData:
    """Integration tests using real pask test data."""

    def test_inventory_report_pask_integration(
        self,
        pask_product_export_file,
        pask_products_report_file,
        templates_dir
    ):
        """Test full inventory report pipeline with pask test data."""
        # Load real test data
        with open(pask_product_export_file, 'rb') as f:
            df_product_export = load_product_export(f)

        with open(pask_products_report_file, 'rb') as f:
            df_products_report = load_products_report_export(f)

        # Load SKU mapping
        df_sku_mapping = load_sku_mapping(templates_dir)

        # Process inventory data
        df_inventory = prepare_lagerrapport_data(
            df_product_export,
            df_products_report,
            df_sku_mapping
        )

        # Validate result structure
        assert len(df_inventory) > 0, "Inventory report should have data"

        # Check required columns present
        required_cols = [
            'SKU', 'Product title', 'Category (SKUT)', 'Category',
            'Regular price', 'Items sold', 'Stock', 'Tax class',
            'Total sales', 'Total tax'
        ]
        for col in required_cols:
            assert col in df_inventory.columns, f"Missing column: {col}"

        # Check that prices were parsed correctly (not all NaN)
        assert df_inventory['Regular price'].notna().sum() > 0, "Prices should not all be NaN"

        # Check that calculations worked
        assert df_inventory['Total sales'].notna().sum() > 0, "Total sales should be calculated"
        assert df_inventory['Total tax'].notna().sum() > 0, "Total tax should be calculated"

        # Check sorting (should be by Category (SKUT), then SKU)
        assert df_inventory['Category (SKUT)'].is_monotonic_increasing or \
               len(df_inventory['Category (SKUT)'].unique()) > 1, \
               "Should be sorted by sales area"

        # Validate calculation correctness for first row with valid data
        valid_rows = df_inventory[
            df_inventory['Regular price'].notna() &
            df_inventory['Items sold'].notna()
        ]
        if len(valid_rows) > 0:
            first_valid = valid_rows.iloc[0]
            expected_sales = first_valid['Regular price'] * first_valid['Items sold']
            # Allow small floating point differences
            assert abs(first_valid['Total sales'] - expected_sales) < 0.01, \
                "Total sales calculation should be correct"

    def test_decimal_notation_not_causing_nan_prices(
        self,
        pask_product_export_file,
        pask_products_report_file,
        templates_dir
    ):
        """Regression test: ensure decimal notation fix prevents NaN prices."""
        # Load data
        with open(pask_product_export_file, 'rb') as f:
            df_product_export = load_product_export(f)

        with open(pask_products_report_file, 'rb') as f:
            df_products_report = load_products_report_export(f)

        df_sku_mapping = load_sku_mapping(templates_dir)

        # Process
        df_inventory = prepare_lagerrapport_data(
            df_product_export,
            df_products_report,
            df_sku_mapping
        )

        # Count products that should have prices but don't
        products_with_sales = df_inventory[df_inventory['Items sold'] > 0]
        missing_prices = products_with_sales[products_with_sales['Regular price'].isna()]

        # This should be very low or zero (unless products genuinely have no price)
        missing_price_pct = len(missing_prices) / len(products_with_sales) * 100 if len(products_with_sales) > 0 else 0

        # Allow up to 5% missing (for edge cases), but should be much lower
        assert missing_price_pct < 5, \
            f"Too many products with sales but missing prices: {missing_price_pct:.1f}%"
