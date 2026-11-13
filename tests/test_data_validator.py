"""Tests for data validation functions."""

import pytest
import pandas as pd

from src.data_validator import (
    validate_data,
    remove_duplicate_bookings,
    validate_inventory_data,
    ValidationResult,
)


class TestValidateData:
    """Tests for validate_data() - validates order report data."""

    CHECKS = [
        'orders_no_timeslot', 'timeslots_no_order', 'incomplete_timeslots',
        'duplicate_bookings', 'missing_products', 'missing_categories',
    ]

    def test_result_structure(self, pask_data):
        """Every check is exposed as a DataFrame attribute and in the summary."""
        result = validate_data(pask_data.orders, pask_data.timeslots,
                               pask_data.products, pask_data.packing)

        assert isinstance(result, ValidationResult)
        summary = result.get_summary()
        assert set(summary) == set(self.CHECKS)
        for check in self.CHECKS:
            df = getattr(result, check)
            assert isinstance(df, pd.DataFrame), f"{check} should be a DataFrame"
            assert summary[check] == len(df)

    def test_pask_fixture_known_issues(self, pask_data):
        """Pin the issue counts in the obfuscated pask fixture."""
        result = validate_data(pask_data.orders, pask_data.timeslots,
                               pask_data.products, pask_data.packing)

        assert result.get_summary() == {
            'orders_no_timeslot': 10,
            'timeslots_no_order': 10,
            'incomplete_timeslots': 0,
            'duplicate_bookings': 0,
            'missing_products': 0,
            'missing_categories': 0,
        }
        assert result.has_errors()

    def test_detects_each_issue_type(self):
        """Synthetic data that triggers every check exactly once."""
        orders = pd.DataFrame({
            'OrderNumber': [1, 2, 3],
            'FullName': ['A', 'B', 'C'],
            'Email': ['a@x.se', 'b@x.se', 'c@x.se'],
            'OrderTotalAmount': [10, 20, 30],
            'OrderDate': ['2026-01-01'] * 3,
            'CustomerNote': [None] * 3,
            'PhoneOrder': [None] * 3,
            'ArticleNumber': ['#A#', '#B#', '#UNKNOWN#'],
            'ProductName': ['a', 'b', 'u'],
            'PackingCategory': ['kakor', 'okand', 'kakor'],
            'PackingCategoryKey': ['kakor', 'okand', 'kakor'],
        })
        timeslots = pd.DataFrame({
            'Email': ['a@x.se', 'b@x.se', 'b@x.se', 'z@x.se', None],
            'PickUpDate': pd.to_datetime(['2026-03-21'] * 5),
            'PickUpTime': ['10:00', '10:00', '11:00', '12:00', '13:00'],
            'FullNameTimeslot': ['A', 'B', 'B', 'Z', 'N'],
            'Telephone': [None] * 5,
        })
        products = pd.DataFrame({'ArticleNumber': ['#A#', '#B#']})
        packing = pd.DataFrame({'PackingCategoryKey': ['kakor']})

        result = validate_data(orders, timeslots, products, packing)

        assert list(result.orders_no_timeslot['OrderNumber']) == [3]
        assert list(result.timeslots_no_order['Email']) == ['z@x.se']
        assert len(result.incomplete_timeslots) == 1
        assert set(result.duplicate_bookings['Email']) == {'b@x.se'}
        assert list(result.missing_products['ArticleNumber']) == ['#UNKNOWN#']
        assert list(result.missing_categories['PackingCategory']) == ['okand']


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

    def test_result_structure(self, pask_inventory):
        result = validate_inventory_data(
            pask_inventory.product_export,
            pask_inventory.products_report,
            pask_inventory.inventory,
        )

        assert set(result) == {
            'is_valid', 'warnings', 'sku_mismatches',
            'unmapped_skus', 'missing_prices', 'missing_stock',
        }
        assert isinstance(result['is_valid'], bool)
        assert isinstance(result['warnings'], list)
        assert isinstance(result['sku_mismatches'], list)
        for key in ('unmapped_skus', 'missing_prices', 'missing_stock'):
            assert isinstance(result[key], pd.DataFrame), key

    def test_detects_missing_prices_and_sku_mismatch(self):
        product_export = pd.DataFrame({'SKU': ['#T1#', '#T2#']})
        products_report = pd.DataFrame({'SKU': ['#T1#', '#T2#', '#ONLY_IN_REPORT#']})
        merged = pd.DataFrame({
            'SKU': ['#T1#', '#T2#'],
            'Category (SKUT)': ['Café', 'Unknown'],
            'Regular price': [10.5, None],
            'Stock': [3, None],
        })

        result = validate_inventory_data(product_export, products_report, merged)

        assert result['is_valid'] is False
        assert result['sku_mismatches'] == ['#ONLY_IN_REPORT#']
        assert list(result['unmapped_skus']['SKU']) == ['#T2#']
        assert list(result['missing_prices']['SKU']) == ['#T2#']
        assert list(result['missing_stock']['SKU']) == ['#T2#']
        assert len(result['warnings']) == 4
