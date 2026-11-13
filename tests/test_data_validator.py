"""Tests for data validation functions."""

from datetime import date, time

import pytest
import pandas as pd

from src.data_processor import merge_all_data
from src.data_validator import (
    CHECKS,
    REASON_NO_CATEGORY,
    REASON_NO_PRODUCT,
    REASON_NO_TIMESLOT,
    validate_data,
    remove_duplicate_bookings,
    validate_inventory_data,
    InventoryValidationResult,
    ValidationResult,
)

CHECK_NAMES = [attr for attr, _ in CHECKS]


def _orders(**overrides):
    """Minimal orders frame; one line per order unless overridden."""
    data = {
        'OrderNumber': [1, 2, 3, 4, 5],
        'FullName': ['A', 'B', 'C', 'D', 'E'],
        'Email': ['a@x.se', 'b@x.se', 'c@x.se', 'd@x.se', None],
        'OrderTotalAmount': [10, 20, 30, 40, 50],
        'OrderDate': ['2026-01-01'] * 5,
        'CustomerNote': [None] * 5,
        'PhoneOrder': [None] * 5,
        'ArticleNumber': ['#A#', '#B#', '#UNKNOWN#', '#A#', '#A#'],
        'ProductName': ['a', 'b', 'u', 'a', 'a'],
        'Quantity': [1, 1, 1, 1, 1],
        'PackingCategory': ['kakor', 'okand', 'kakor', 'kakor', 'kakor'],
    }
    data.update(overrides)
    df = pd.DataFrame(data)
    df['PackingCategoryKey'] = df['PackingCategory'].str.lower()
    return df


def _timeslots():
    return pd.DataFrame({
        'Email': ['a@x.se', 'b@x.se', 'b@x.se', 'c@x.se', 'z@x.se', None, 'd@x.se'],
        'PickUpDate': pd.to_datetime(['2026-03-21'] * 7),
        'PickUpTime': [time(10), time(10), time(11), time(10), time(12), time(13), time(15)],
        'FullNameTimeslot': ['A', 'B', 'B', 'C', 'Z', 'N', 'D'],
        'Telephone': [None] * 7,
    })


def _schedule():
    return pd.DataFrame({
        'Date': [date(2026, 3, 21)] * 4,
        'Tid': [time(10), time(11), time(12), time(13)],
    })


class TestValidateData:
    """Tests for validate_data() - validates order report data."""

    def test_result_structure(self, pask_data):
        """Every check is exposed as a DataFrame attribute and in the summary."""
        result = validate_data(pask_data.orders, pask_data.timeslots,
                               pask_data.products, pask_data.packing, pask_data.schedule)

        assert isinstance(result, ValidationResult)
        summary = result.get_summary()
        assert list(summary) == CHECK_NAMES
        for check in CHECK_NAMES:
            df = getattr(result, check)
            assert isinstance(df, pd.DataFrame), f"{check} should be a DataFrame"
            assert summary[check] == len(df)
        assert isinstance(result.excluded_order_lines, pd.DataFrame)

    def test_pask_fixture_known_issues(self, pask_data):
        """Pin the issue counts in the obfuscated pask fixture."""
        result = validate_data(pask_data.orders, pask_data.timeslots,
                               pask_data.products, pask_data.packing, pask_data.schedule)

        assert result.get_summary() == {
            'orders_no_timeslot': 10,
            'timeslots_no_order': 10,
            'incomplete_timeslots': 0,
            'duplicate_bookings': 0,
            'bookings_outside_schedule': 0,
            'missing_products': 0,
            'duplicate_products': 0,
            'missing_categories': 0,
            'duplicate_categories': 0,
        }
        assert result.has_errors()
        assert set(result.excluded_order_lines['Reason']) == {REASON_NO_TIMESLOT}

    def test_detects_each_issue_type(self):
        """Synthetic data that triggers every check."""
        products = pd.DataFrame({'ArticleNumber': ['#A#', '#B#', '#B#']})
        packing = pd.DataFrame({'PackingCategoryKey': ['kakor', 'godis', 'godis']})

        result = validate_data(_orders(), _timeslots(), products, packing, _schedule())

        assert list(result.orders_no_timeslot['OrderNumber']) == [5]   # no email
        assert list(result.timeslots_no_order['Email']) == ['z@x.se']
        assert len(result.incomplete_timeslots) == 1
        assert set(result.duplicate_bookings['Email']) == {'b@x.se'}
        assert list(result.bookings_outside_schedule['Email']) == ['d@x.se']  # 15:00
        assert list(result.missing_products['ArticleNumber']) == ['#UNKNOWN#']
        assert list(result.duplicate_products['ArticleNumber']) == ['#B#', '#B#']
        assert list(result.missing_categories['PackingCategory']) == ['okand']
        assert list(result.duplicate_categories['PackingCategoryKey']) == ['godis', 'godis']

        excluded = result.excluded_order_lines.set_index('OrderNumber')['Reason']
        assert excluded.to_dict() == {
            2: REASON_NO_CATEGORY,
            3: REASON_NO_PRODUCT,
            5: REASON_NO_TIMESLOT,
        }

    def test_missing_packing_category_is_reported(self):
        """An order line without category ('' after loading) is reported."""
        orders = _orders(PackingCategory=['kakor', '', 'kakor', 'kakor', 'kakor'])
        products = pd.DataFrame({'ArticleNumber': ['#A#', '#B#', '#UNKNOWN#']})
        packing = pd.DataFrame({'PackingCategoryKey': ['kakor']})

        result = validate_data(orders, _timeslots(), products, packing)

        assert list(result.missing_categories['OrderNumber']) == [2]

    @pytest.mark.parametrize('use_fixture', [True, False])
    def test_excluded_lines_match_merge(self, use_fixture, pask_data):
        """excluded_order_lines must be exactly what merge_all_data() drops."""
        if use_fixture:
            orders, timeslots = pask_data.orders, pask_data.timeslots
            products, packing = pask_data.products, pask_data.packing
        else:
            orders, timeslots = _orders(), _timeslots()
            products = pd.DataFrame({'ArticleNumber': ['#A#', '#B#', '#B#']})
            packing = pd.DataFrame({'PackingCategoryKey': ['kakor', 'godis'],
                                    'PickUpArea': ['K', 'G'],
                                    'PackingCategoryIndex': [0, 1]})

        result = validate_data(orders, timeslots, products, packing)
        merged = merge_all_data(orders.assign(_line=range(len(orders))),
                                remove_duplicate_bookings(timeslots), products, packing)

        kept = set(merged['_line'])
        excluded = set(range(len(orders))) - kept
        assert len(merged) == len(kept), "merge must not duplicate order lines"
        assert len(result.excluded_order_lines) == len(excluded)


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

        assert isinstance(result, InventoryValidationResult)
        assert isinstance(result.warnings, list)
        assert isinstance(result.sku_mismatches, list)
        for attr in ('unmapped_skus', 'missing_prices', 'missing_stock'):
            assert isinstance(getattr(result, attr), pd.DataFrame), attr

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

        assert result.sku_mismatches == ['#ONLY_IN_REPORT#']
        assert list(result.unmapped_skus['SKU']) == ['#T2#']
        assert list(result.missing_prices['SKU']) == ['#T2#']
        assert list(result.missing_stock['SKU']) == ['#T2#']
        assert len(result.warnings) == 4
