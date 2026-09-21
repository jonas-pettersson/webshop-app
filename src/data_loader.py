"""Data loading functions for WebShop Report system.

Handles loading and initial formatting of data from WordPress exports
and template files.
"""

from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Union
import shutil

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

    # Create packing category key
    df['PackingCategory'] = df['PackingCategory'].transform(lambda x: str(x))
    df['PackingCategoryKey'] = df['PackingCategory'].str.lower()

    return df


def load_timeslots(file_obj: BinaryIO, market_type: str) -> pd.DataFrame:
    """Load and format timeslot bookings from WP Time Slots plugin CSV export.

    Handles different date formats between market types and encoding issues.

    Args:
        file_obj: File object containing CSV data
        market_type: One of config.MARKET_TYPES (affects date parsing)

    Returns:
        DataFrame with columns: OrderTime, Email, PickUpDate, PickUpTime,
                                PickUpDateTime, FullNameTimeslot, Telephone
    """
    # Note: The check for market type is kept for backward compatibility,
    # but currently all market types use the same parsing logic
    df = pd.read_csv(
        file_obj,
        index_col=False,
        parse_dates=['Time', 'app_date_1', 'Select Date and Time'],
        dayfirst=False,
        usecols=[
            'Time', 'Email',
            'app_date_1', 'app_slot_1', 'Select Date and Time',
            'Name', 'Telefon'
        ],
        encoding='latin_1'
    )

    df.columns = [
        'OrderTime', 'Email',
        'PickUpDate', 'PickUpTime', 'PickUpDateTime',
        'FullNameTimeslot', 'Telephone'
    ]

    # Convert pick-up time from string to real time format
    df['PickUpTime'] = df['PickUpTime'].transform(
        lambda t: datetime.strptime(t, '%H:%M').time()
    )

    # Convert emails to lowercase for matching
    df['Email'] = df['Email'].str.lower()

    return df


def load_packing_categories(market_type: str, template_dir: Path) -> pd.DataFrame:
    """Load packing categories from market-specific template file.

    The template file is copied from templates/ directory as it may be modified.

    Args:
        market_type: One of config.MARKET_TYPES
        template_dir: Path to templates directory

    Returns:
        DataFrame with columns: PickUpArea, PackingCategory, PackingCategoryKey,
                                PackingCategoryIndex
    """
    template_path = config.get_template_path(
        template_dir,
        config.TEMPLATE_FILENAME_PACKING_CATEGORIES,
        market_type
    )

    df = pd.read_excel(
        str(template_path),
        header=1,
        skiprows=None,
        usecols=['info till Packlistan', 'Packningskategori']
    )

    df.columns = ['PickUpArea', 'PackingCategory']

    # Create packing category key
    df['PackingCategory'] = df['PackingCategory'].transform(lambda x: str(x))
    df['PackingCategoryKey'] = df['PackingCategory'].str.lower()

    # Replace underscores in pickup area names
    df['PickUpArea'] = df['PickUpArea'].str.replace('_', ' ')

    # Add index for sorting
    df['PackingCategoryIndex'] = df.index

    return df


def load_schedule(market_type: str, template_dir: Path) -> pd.DataFrame:
    """Load pickup schedule from market-specific template file.

    Args:
        market_type: One of config.MARKET_TYPES
        template_dir: Path to templates directory

    Returns:
        DataFrame with columns: Dag, Tid, Date, DateTime
    """
    template_path = config.get_template_path(
        template_dir,
        config.TEMPLATE_FILENAME_SCHEDULE,
        market_type
    )

    df = pd.read_excel(str(template_path))

    # Create additional date and datetime columns
    df['Date'] = df['Dag'].transform(lambda x: x.date())
    df['DateTime'] = [
        datetime.combine(d, t) for d, t in zip(df['Dag'], df['Tid'])
    ]

    return df
