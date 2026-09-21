"""Data processing and merging for WebShop Report system.

Combines orders, timeslots, products, and packing categories into
a unified dataset for report generation.
"""

import pandas as pd


def merge_all_data(
    orders_df: pd.DataFrame,
    timeslots_df: pd.DataFrame,
    products_df: pd.DataFrame,
    packing_df: pd.DataFrame
) -> pd.DataFrame:
    """Merge all datasets into comprehensive allData DataFrame.

    Performs sequential joins:
    1. Orders + Timeslots (on Email)
    2. + Products (on ArticleNumber)
    3. + Packing Categories (on PackingCategoryKey)

    Args:
        orders_df: Orders DataFrame (cleaned)
        timeslots_df: Timeslots DataFrame (duplicates already removed)
        products_df: Products DataFrame
        packing_df: Packing categories DataFrame

    Returns:
        Merged DataFrame with all information needed for report generation
    """
    # Merge orders with timeslots on Email
    all_data = pd.merge(orders_df, timeslots_df, on='Email')

    # Merge with products on ArticleNumber
    all_data = pd.merge(
        all_data,
        products_df,
        on='ArticleNumber',
        suffixes=['', None]
    )

    # Merge with packing categories on PackingCategoryKey
    all_data = pd.merge(all_data, packing_df, on='PackingCategoryKey')

    return all_data


def sort_for_reports(all_data_df: pd.DataFrame) -> pd.DataFrame:
    """Sort data by pickup date, time, and packing category for report generation.

    Args:
        all_data_df: Merged DataFrame from merge_all_data()

    Returns:
        Sorted DataFrame ready for report generation
    """
    return all_data_df.sort_values(
        by=['PickUpDate', 'PickUpTime', 'PackingCategoryIndex']
    )
