"""Data loading functions for WebShop Report system.

Handles loading and initial formatting of data from WordPress exports
and template files.
"""

from datetime import datetime
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from . import config


def load_products(file_obj: BinaryIO) -> pd.DataFrame:
    """Load and format product catalog from WordPress export CSV.

    Args:
        file_obj: File object containing CSV data

    Returns:
        DataFrame with columns: ArticleNumber, ProductDescription, RegularPrice
    """
    df = pd.read_csv(
        file_obj,
        usecols=['SKU', 'Short description', 'Regular price']
    )

    df.columns = ['ArticleNumber', 'ProductDescription', 'RegularPrice']

    return df


def load_orders(file_obj: BinaryIO) -> pd.DataFrame:
    """Load and format orders from WooCommerce export Excel file.

    Performs email normalization and packing category key creation.

    Args:
        file_obj: File object containing Excel data

    Returns:
        DataFrame with normalized columns and PackingCategoryKey added
    """
    df = pd.read_excel(
        file_obj,
        usecols=[
            'Order Number', 'Full Name (Billing)', 'Email (Billing)',
            'Order Total Amount (- Refund)', 'Order Date', 'Customer Note',
            'Phone (Billing)', 'SKU', 'Quantity (- Refund)', 'Product Name',
            'Item Cost (inc. tax)', 'Item #', 'Info', 'pa_packn_kategori'
        ]
    )

    df.columns = [
        'OrderNumber', 'FullName', 'Email',
        'OrderTotalAmount', 'OrderDate', 'CustomerNote',
        'PhoneOrder', 'ArticleNumber', 'Quantity', 'ProductName',
        'ItemCost', 'ItemID', 'Info', 'PackingCategory'
    ]

    # Convert emails to lowercase for matching
    df['Email'] = df['Email'].str.lower()

    # Create packing category key. A missing category becomes '' (not the
    # string 'nan'), so it can never match a packing template row and is
    # reported by validation as a missing category.
    df['PackingCategory'] = df['PackingCategory'].fillna('').astype(str)
    df['PackingCategoryKey'] = df['PackingCategory'].str.lower()

    return df


def load_timeslots(file_obj: BinaryIO) -> pd.DataFrame:
    """Load and format timeslot bookings from WP Time Slots plugin CSV export.

    Args:
        file_obj: File object containing CSV data

    Returns:
        DataFrame with columns: OrderTime, Email, PickUpDate, PickUpTime,
                                PickUpDateTime, FullNameTimeslot, Telephone
    """
    df = pd.read_csv(
        file_obj,
        index_col=False,
        usecols=[
            'Time', 'Email',
            'app_date_1', 'app_slot_1', 'Select Date and Time',
            'Name', 'Telefon'
        ],
        encoding='latin_1'
    )

    # Parse dates explicitly to avoid format inference warnings
    df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    df['app_date_1'] = pd.to_datetime(df['app_date_1'], format='%Y-%m-%d', errors='coerce')
    # Select Date and Time has a complex format with extra data, parse the first two parts
    df['Select Date and Time'] = pd.to_datetime(
        df['Select Date and Time'].str.split(' ').str[:2].str.join(' '),
        format='%Y-%m-%d %H:%M',
        errors='coerce'
    )

    df.columns = [
        'OrderTime', 'Email',
        'PickUpDate', 'PickUpTime', 'PickUpDateTime',
        'FullNameTimeslot', 'Telephone'
    ]

    # Convert pick-up time from string to real time format
    # Handle empty strings and NaN values
    df['PickUpTime'] = df['PickUpTime'].apply(
        lambda t: datetime.strptime(t, '%H:%M').time() if pd.notna(t) and t.strip() != '' else pd.NaT
    )

    # Convert emails to lowercase for matching
    df['Email'] = df['Email'].str.lower()

    return df


def load_packing_categories(template_path: Path) -> pd.DataFrame:
    """Load packing categories (placeringsnycklar_<market>.xlsx).

    Args:
        template_path: Path to the market's packing categories file

    Returns:
        DataFrame with columns: PickUpArea, PackingCategory, PackingCategoryKey,
                                PackingCategoryIndex
    """
    df = pd.read_excel(
        str(template_path),
        header=1,
        skiprows=None,
        usecols=['info till Packlistan', 'Packningskategori']
    )

    df.columns = ['PickUpArea', 'PackingCategory']

    # Add index for sorting (before dropping rows: the template's row
    # position defines the packing order)
    df['PackingCategoryIndex'] = df.index

    # Blank template rows are visual separators, not categories. Left in,
    # each would become a 'nan' key and multiply uncategorized order lines.
    df = df.dropna(subset=['PackingCategory']).copy()

    # Create packing category key
    df['PackingCategory'] = df['PackingCategory'].astype(str)
    df['PackingCategoryKey'] = df['PackingCategory'].str.lower()

    # Replace underscores in pickup area names
    df['PickUpArea'] = df['PickUpArea'].str.replace('_', ' ')

    return df[['PickUpArea', 'PackingCategory', 'PackingCategoryKey', 'PackingCategoryIndex']]


def load_schedule(template_path: Path) -> pd.DataFrame:
    """Load pickup schedule (schedule_<market>.xlsx).

    Args:
        template_path: Path to the market's schedule file

    Returns:
        DataFrame with columns: Dag, Tid, Date, DateTime
    """
    df = pd.read_excel(str(template_path))

    # Create additional date and datetime columns
    df['Date'] = df['Dag'].transform(lambda x: x.date())
    df['DateTime'] = [
        datetime.combine(d, t) for d, t in zip(df['Dag'], df['Tid'])
    ]

    return df


def load_product_export(file_obj: BinaryIO) -> pd.DataFrame:
    """Load full product catalog from wc-product-export.csv for inventory report.

    Args:
        file_obj: File object containing CSV data

    Returns:
        DataFrame with columns: SKU, Name, Regular price, Stock, Tax status, Tax class
    """
    df = pd.read_csv(
        file_obj,
        usecols=['SKU', 'Name', 'Regular price', 'Stock', 'Tax status', 'Tax class']
    )
    df['SKU'] = df['SKU'].str.strip()
    # Convert numeric columns - handle both English (dot) and German (comma) decimal notation
    df['Regular price'] = df['Regular price'].astype(str).str.replace(',', '.', regex=False)
    df['Regular price'] = pd.to_numeric(df['Regular price'], errors='coerce')
    return df


def load_products_report_export(file_obj: BinaryIO) -> pd.DataFrame:
    """Load product sales report from wc-products-report-export.csv for inventory report.

    Args:
        file_obj: File object containing CSV data

    Returns:
        DataFrame with columns: Product title, SKU, Items sold, N. Revenue, Category, Stock
    """
    df = pd.read_csv(
        file_obj,
        usecols=['Product title', 'SKU', 'Items sold', 'N. Revenue', 'Category', 'Stock']
    )
    df['SKU'] = df['SKU'].str.strip()
    # Convert numeric columns - handle both English (dot) and German (comma) decimal notation
    df['Items sold'] = df['Items sold'].astype(str).str.replace(',', '.', regex=False)
    df['Items sold'] = pd.to_numeric(df['Items sold'], errors='coerce')
    return df


def load_sku_mapping(template_dir: Path) -> pd.DataFrame:
    """Load SKU prefix to sales area mapping from template file.

    Args:
        template_dir: Path to templates directory

    Returns:
        DataFrame with columns: SKU_Prefix, Sales_Area
    """
    template_path = template_dir / config.TEMPLATE_FILENAME_SKU_MAPPING
    df = pd.read_excel(str(template_path), sheet_name='Mapping')
    return df
