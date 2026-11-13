"""Data validation for WebShop Report system.

Validates relationships between orders, timeslots, products, and packing categories.
Generates comprehensive validation report (diffs.xlsx).

All findings are warnings: report generation always proceeds, and every
affected row is listed in diffs.xlsx so nothing disappears silently.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data_processor import prepare_merge_inputs
from .excel_utils import dataframe_to_xlsx_bytes
from .lagerrapport_processor import UNKNOWN_SALES_AREA

TIMESLOT_COLUMNS = ['Email', 'PickUpDate', 'PickUpTime', 'FullNameTimeslot', 'Telephone']

# Every check: (ValidationResult attribute, UI label)
CHECKS = [
    ('orders_no_timeslot', 'Orders w/o Timeslot'),
    ('timeslots_no_order', 'Timeslots w/o Order'),
    ('incomplete_timeslots', 'Incomplete Timeslots'),
    ('duplicate_bookings', 'Duplicate Bookings'),
    ('bookings_outside_schedule', 'Outside Schedule'),
    ('missing_products', 'Missing Products'),
    ('duplicate_products', 'Duplicate Products'),
    ('missing_categories', 'Missing Categories'),
    ('duplicate_categories', 'Duplicate Categories'),
]

# Reasons an order line is excluded from packing/pickup lists
REASON_NO_TIMESLOT = 'Ingen tidsbokning'
REASON_NO_PRODUCT = 'Saknas i produktlista'
REASON_NO_CATEGORY = 'Packningskategori saknas'


class ValidationResult:
    """Container for validation results (one DataFrame per check)."""

    def __init__(self):
        for attr, _ in CHECKS:
            setattr(self, attr, pd.DataFrame())
        # Derived: order lines that will NOT appear in packing/pickup lists
        self.excluded_order_lines = pd.DataFrame()

    def has_errors(self) -> bool:
        """Check if any validation issues were found."""
        return any(count > 0 for count in self.get_summary().values())

    def get_summary(self) -> dict[str, int]:
        """Get count of each validation issue type."""
        return {attr: len(getattr(self, attr)) for attr, _ in CHECKS}


def validate_data(
    orders_df: pd.DataFrame,
    timeslots_df: pd.DataFrame,
    products_df: pd.DataFrame,
    packing_df: pd.DataFrame,
    schedule_df: pd.DataFrame = None
) -> ValidationResult:
    """Validate relationships between all datasets.

    Checks for:
    - Orders without time bookings (including orders without email)
    - Time bookings without orders
    - Incomplete time bookings (missing email, pickup date or pickup time)
    - Duplicate time bookings (multiple per email)
    - Bookings at a date/time that is not in the pickup schedule
    - Products in orders but not in product catalog
    - Duplicate SKUs in the product catalog
    - Packing categories in orders but not defined
    - Duplicate packing categories in the template

    Also lists every order line that will be excluded from the reports,
    with the reason (excluded_order_lines).

    Args:
        orders_df: Orders DataFrame
        timeslots_df: Timeslots DataFrame
        products_df: Products DataFrame
        packing_df: Packing categories DataFrame
        schedule_df: Schedule DataFrame (optional; enables the schedule check)

    Returns:
        ValidationResult object containing all validation issues
    """
    result = ValidationResult()

    # 1. Orders without time bookings (orders without email can't be matched either)
    order_emails = orders_df['Email'].dropna().unique()
    timeslot_emails = timeslots_df['Email'].dropna().unique()
    diff_emails = np.setdiff1d(order_emails, timeslot_emails)

    result.orders_no_timeslot = orders_df[
        orders_df['Email'].isin(diff_emails) | orders_df['Email'].isna()
    ].drop_duplicates(subset=['OrderNumber'])[[
        'OrderNumber', 'FullName', 'Email',
        'OrderTotalAmount', 'OrderDate', 'CustomerNote', 'PhoneOrder'
    ]]

    # 2. Time bookings without orders (only valid timeslots with emails)
    diff_emails = np.setdiff1d(timeslot_emails, order_emails)
    result.timeslots_no_order = timeslots_df[
        timeslots_df['Email'].isin(diff_emails)
    ][TIMESLOT_COLUMNS]

    # 2b. Incomplete timeslots (missing email, date or time) - data quality issue
    result.incomplete_timeslots = timeslots_df[
        timeslots_df['Email'].isna()
        | timeslots_df['PickUpDate'].isna()
        | timeslots_df['PickUpTime'].isna()
    ][TIMESLOT_COLUMNS]

    # 3. Duplicate time bookings (excluding NaN emails)
    email_counts = timeslots_df['Email'].dropna().value_counts()
    duplicate_emails = email_counts.index[email_counts.gt(1)]
    result.duplicate_bookings = timeslots_df[
        timeslots_df['Email'].isin(duplicate_emails)
    ].sort_values(by=['Email', 'PickUpDate', 'PickUpTime'])[TIMESLOT_COLUMNS]

    # 3b. Bookings outside the pickup schedule
    if schedule_df is not None:
        result.bookings_outside_schedule = find_bookings_outside_schedule(
            timeslots_df, schedule_df
        )[TIMESLOT_COLUMNS]

    # 4. Products in orders but missing from product catalog
    order_skus = orders_df['ArticleNumber'].dropna().unique()
    product_skus = products_df['ArticleNumber'].dropna().unique()
    sku_diff = np.setdiff1d(order_skus, product_skus)

    result.missing_products = orders_df[
        orders_df['ArticleNumber'].isin(sku_diff)
    ][['ArticleNumber', 'ProductName']].drop_duplicates(
        subset=['ArticleNumber']
    ).sort_values(by='ArticleNumber')

    # 4b. Duplicate SKUs in product catalog (the first occurrence is used)
    result.duplicate_products = products_df[
        products_df['ArticleNumber'].notna()
        & products_df['ArticleNumber'].duplicated(keep=False)
    ].sort_values(by='ArticleNumber')

    # 5. Packing categories in orders but not defined
    order_categories = orders_df['PackingCategoryKey'].dropna().unique()
    packing_categories = packing_df['PackingCategoryKey'].dropna().unique()
    category_diff = np.setdiff1d(order_categories, packing_categories)

    result.missing_categories = orders_df[
        orders_df['PackingCategoryKey'].isin(category_diff)
    ][[
        'PackingCategory', 'OrderNumber', 'ArticleNumber',
        'ProductName', 'FullName', 'Email'
    ]].sort_values(by='PackingCategory')

    # 5b. Duplicate packing categories in template (the first occurrence is used)
    result.duplicate_categories = packing_df[
        packing_df['PackingCategoryKey'].notna()
        & packing_df['PackingCategoryKey'].duplicated(keep=False)
    ].sort_values(by='PackingCategoryKey')

    # 6. Order lines that will be excluded from the reports
    result.excluded_order_lines = find_excluded_order_lines(
        orders_df, timeslots_df, products_df, packing_df
    )

    return result


def find_bookings_outside_schedule(
    timeslots_df: pd.DataFrame,
    schedule_df: pd.DataFrame
) -> pd.DataFrame:
    """Bookings (with date and time) whose slot is not in the schedule."""
    scheduled = set(zip(schedule_df['Date'], schedule_df['Tid'], strict=True))
    booked = timeslots_df.dropna(subset=['PickUpDate', 'PickUpTime'])
    outside = [
        (date.date(), time) not in scheduled
        for date, time in zip(booked['PickUpDate'], booked['PickUpTime'], strict=True)
    ]
    return booked[outside]


def find_excluded_order_lines(
    orders_df: pd.DataFrame,
    timeslots_df: pd.DataFrame,
    products_df: pd.DataFrame,
    packing_df: pd.DataFrame
) -> pd.DataFrame:
    """Order lines that merge_all_data() will drop, with the (first) reason.

    Mirrors merge_all_data(): uses the same prepare_merge_inputs(), and an
    inner join on a key drops exactly the rows whose key is missing on the
    right-hand side.
    """
    timeslots, products, packing = prepare_merge_inputs(timeslots_df, products_df, packing_df)

    no_timeslot = ~orders_df['Email'].isin(timeslots['Email'])
    no_product = ~orders_df['ArticleNumber'].isin(products['ArticleNumber'])
    no_category = ~orders_df['PackingCategoryKey'].isin(packing['PackingCategoryKey'])

    reason = np.select(
        [no_timeslot, no_product, no_category],
        [REASON_NO_TIMESLOT, REASON_NO_PRODUCT, REASON_NO_CATEGORY],
        default=''
    )
    excluded = orders_df[[
        'OrderNumber', 'FullName', 'Email', 'ArticleNumber', 'ProductName',
        'Quantity', 'PackingCategory'
    ]].assign(Reason=reason)
    return excluded[excluded['Reason'] != '']


# (diffs.xlsx sheet name, ValidationResult attribute) - in sheet order.
# The first six are the original notebook's sheets.
DIFFS_SHEETS = [
    ('Beställning utan tidsbokning', 'orders_no_timeslot'),
    ('Tidsbokning utan beställning', 'timeslots_no_order'),
    ('Ofullständiga tidsbokningar', 'incomplete_timeslots'),
    ('Dubbla tidsbokningar', 'duplicate_bookings'),
    ('Saknas i produktlista', 'missing_products'),
    ('Packningskategori saknas', 'missing_categories'),
    ('Utanför hämtschema', 'bookings_outside_schedule'),
    ('Dubbla produkter', 'duplicate_products'),
    ('Dubbla packningskategorier', 'duplicate_categories'),
    ('Saknas i packlistor', 'excluded_order_lines'),
]


def generate_diffs_report(validation_result: ValidationResult) -> bytes:
    """Build the validation report (diffs.xlsx), one sheet per check.

    Args:
        validation_result: ValidationResult object from validate_data()

    Returns:
        bytes: The .xlsx file content
    """
    sheets = {
        sheet_name: getattr(validation_result, attr)
        for sheet_name, attr in DIFFS_SHEETS
    }
    return dataframe_to_xlsx_bytes(sheets, align_widths=True)


def remove_duplicate_bookings(timeslots_df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate time bookings, keeping only the first booking per email.

    This should be called AFTER validation report is generated, so duplicates
    are reported but then removed for processing. Bookings without email are
    all kept (they are reported as incomplete and can't match an order).

    Args:
        timeslots_df: Timeslots DataFrame (will not be modified)

    Returns:
        New DataFrame with duplicates removed
    """
    has_email = timeslots_df['Email'].notna()
    deduped = timeslots_df[has_email].drop_duplicates(subset=['Email'], keep='first')
    return pd.concat([deduped, timeslots_df[~has_email]]).sort_index()


@dataclass
class InventoryValidationResult:
    """Inventory (lagerrapport) validation findings. All are warnings."""

    sku_mismatches: list         # SKUs in the sales report but not in the product export
    unmapped_skus: pd.DataFrame  # products whose sales area is unknown
    missing_prices: pd.DataFrame
    missing_stock: pd.DataFrame

    @property
    def warnings(self) -> list[str]:
        """One summary message per check that found something."""
        messages = [
            (len(self.sku_mismatches), "⚠️ {} SKU(s) not found in product export"),
            (len(self.unmapped_skus), "⚠️ {} product(s) have unknown sales area"),
            (len(self.missing_prices), "⚠️ {} product(s) have missing price data"),
            (len(self.missing_stock), "ℹ️ {} product(s) have missing stock data"),
        ]
        return [text.format(count) for count, text in messages if count > 0]


def validate_inventory_data(
    product_export_df: pd.DataFrame,
    products_report_df: pd.DataFrame,
    merged_df: pd.DataFrame
) -> InventoryValidationResult:
    """Validate inventory data for lagerrapport generation.

    Args:
        product_export_df: Full product catalog DataFrame
        products_report_df: Sales report DataFrame
        merged_df: Output of prepare_lagerrapport_data()

    Returns:
        InventoryValidationResult
    """
    report_skus = set(products_report_df['SKU'].dropna())
    export_skus = set(product_export_df['SKU'].dropna())

    return InventoryValidationResult(
        sku_mismatches=sorted(report_skus - export_skus),
        unmapped_skus=merged_df[merged_df['Category (SKUT)'] == UNKNOWN_SALES_AREA],
        missing_prices=merged_df[merged_df['Regular price'].isna()],
        missing_stock=merged_df[merged_df['Stock'].isna()],
    )
