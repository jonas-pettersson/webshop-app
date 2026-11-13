"""Data processing and merging for WebShop Report system.

Combines orders, timeslots, products, and packing categories into
a unified dataset for report generation.
"""


import pandas as pd


def prepare_merge_inputs(
    timeslots_df: pd.DataFrame,
    products_df: pd.DataFrame,
    packing_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Make the right-hand side of every join unique and free of missing keys.

    pandas matches NaN keys with each other and multiplies rows on duplicate
    keys, so without this an order without email would attach to a random
    incomplete booking, and a duplicated SKU would list an item twice.
    Duplicates are reported by validation; here the first occurrence wins.

    Used by both merge_all_data() and validation, so "which order lines end
    up in the reports" is defined in exactly one place.
    """
    def unique_keys(df, key):
        return df.dropna(subset=[key]).drop_duplicates(subset=[key], keep='first')

    timeslots = unique_keys(timeslots_df, 'Email')
    products = unique_keys(products_df, 'ArticleNumber')
    packing = unique_keys(packing_df, 'PackingCategoryKey')
    return timeslots, products, packing


def merge_all_data(
    orders_df: pd.DataFrame,
    timeslots_df: pd.DataFrame,
    products_df: pd.DataFrame,
    packing_df: pd.DataFrame
) -> pd.DataFrame:
    """Merge all datasets into comprehensive allData DataFrame.

    Performs sequential INNER joins (same as the original notebook):
    1. Orders + Timeslots (on Email)
    2. + Products (on ArticleNumber)
    3. + Packing Categories (on PackingCategoryKey)

    Order lines without a match are excluded from the reports; validation
    lists every such line (ValidationResult.excluded_order_lines).

    Args:
        orders_df: Orders DataFrame (cleaned)
        timeslots_df: Timeslots DataFrame (duplicates already removed)
        products_df: Products DataFrame
        packing_df: Packing categories DataFrame

    Returns:
        Merged DataFrame with all information needed for report generation
    """
    timeslots, products, packing = prepare_merge_inputs(timeslots_df, products_df, packing_df)

    all_data = pd.merge(orders_df, timeslots, on='Email', validate='many_to_one')
    all_data = pd.merge(all_data, products, on='ArticleNumber', suffixes=['', None],
                        validate='many_to_one')
    all_data = pd.merge(all_data, packing, on='PackingCategoryKey', validate='many_to_one')

    return all_data


def sort_for_reports(all_data_df: pd.DataFrame) -> pd.DataFrame:
    """Sort data by pickup date, time, and packing category for report generation.

    Rows with missing pickup date/time sort last.

    Args:
        all_data_df: Merged DataFrame from merge_all_data()

    Returns:
        Sorted DataFrame ready for report generation
    """
    return all_data_df.sort_values(
        by=['PickUpDate', 'PickUpTime', 'PackingCategoryIndex']
    )
