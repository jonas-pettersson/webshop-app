"""Lagerrapport (Inventory Report) processing logic.

This module handles the core data processing for generating inventory reports
by combining product catalog data with sales data, mapping SKUs to sales areas,
and calculating totals.
"""

import pandas as pd
from . import config


def map_sku_to_sales_area(sku: str, mapping_df: pd.DataFrame) -> str:
    """Map single SKU to sales area using prefix matching.

    Args:
        sku: Product SKU to map
        mapping_df: DataFrame with SKU_Prefix and Sales_Area columns

    Returns:
        str: Sales area name or "Unknown" if no prefix matches
    """
    if pd.isna(sku):
        return "Unknown"

    sku_str = str(sku)
    for _, row in mapping_df.iterrows():
        if sku_str.startswith(row['SKU_Prefix']):
            return row['Sales_Area']

    return "Unknown"


def get_tax_rate(tax_class: str) -> float:
    """Lookup tax rate from config.TAX_RATES.

    Args:
        tax_class: Tax class string from product data

    Returns:
        float: Tax rate (0.00-0.20)
    """
    if pd.isna(tax_class):
        return config.TAX_RATES[None]
    return config.TAX_RATES.get(tax_class, config.TAX_RATES[None])


def prepare_lagerrapport_data(
    product_export_df: pd.DataFrame,
    products_report_df: pd.DataFrame,
    sku_mapping_df: pd.DataFrame
) -> pd.DataFrame:
    """Main processing pipeline for inventory report data.

    Processing steps:
    1. INNER join product export with sales report on SKU
       (keeps only products with sales activity)
    2. Map SKU to sales area using prefix matching
    3. Calculate totals (Total sales, Total tax)
    4. Select final 10 columns
    5. Sort by sales area, then SKU

    Args:
        product_export_df: Full product catalog (SKU, Name, Price, Stock, Tax)
        products_report_df: Sales report (SKU, Product title, Items sold, etc.)
        sku_mapping_df: SKU prefix to sales area mapping

    Returns:
        DataFrame with 10 columns ready for template insertion:
        - SKU
        - Product title
        - Category (SKUT) [sales area from mapping]
        - Category [from products report]
        - Regular price
        - Items sold
        - Stock
        - Tax class
        - Total sales (price * items sold)
        - Total tax (price * tax rate)
    """
    # 1. INNER join on SKU - keeps only products with sales
    merged_df = products_report_df.merge(
        product_export_df,
        on='SKU',
        how='inner',
        suffixes=('_report', '_export')
    )

    # 2. Map SKU to sales area
    merged_df['Category (SKUT)'] = merged_df['SKU'].apply(
        lambda sku: map_sku_to_sales_area(sku, sku_mapping_df)
    )

    # 3. Calculate totals
    merged_df['Total sales'] = merged_df['Regular price'] * merged_df['Items sold']
    merged_df['Tax rate'] = merged_df['Tax class'].apply(get_tax_rate)
    merged_df['Total tax'] = merged_df['Regular price'] * merged_df['Tax rate']

    # Handle Stock column - use export version (more authoritative)
    merged_df['Stock'] = merged_df['Stock_export']

    # 4. Select final columns (10 columns for the report)
    final_df = merged_df[[
        'SKU',
        'Product title',
        'Category (SKUT)',
        'Category',
        'Regular price',
        'Items sold',
        'Stock',
        'Tax class',
        'Total sales',
        'Total tax'
    ]].copy()

    # 5. Sort by Sales Area, then SKU
    final_df = final_df.sort_values(
        by=['Category (SKUT)', 'SKU'],
        ascending=[True, True]
    ).reset_index(drop=True)

    return final_df
