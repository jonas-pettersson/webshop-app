"""Data loading functions for WebShop Report system.

Handles loading and initial formatting of data from WordPress exports
and template files.

Columns are always selected and renamed *by name* (never by position), so
a WordPress export with reordered or additional columns still loads
correctly; a missing column raises InputFileError naming the column.
"""

import io
import zipfile
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from . import config


class InputFileError(ValueError):
    """An input file doesn't have the expected structure (shown to the user)."""


def _decode_text(file_obj) -> io.StringIO:
    """Read an uploaded text file: UTF-8 (with or without BOM), else latin_1.

    WordPress plugins differ in the encoding they export; latin_1 text with
    Swedish letters is never valid UTF-8, so the first decoding that works
    is the right one.
    """
    raw = file_obj.read()
    try:
        return io.StringIO(raw.decode('utf-8-sig'))
    except UnicodeDecodeError:
        return io.StringIO(raw.decode('latin_1'))


def _read_columns(source, columns: dict, label: str, reader=pd.read_csv, **kwargs) -> pd.DataFrame:
    """Read the given columns from a CSV/Excel file, by name.

    Args:
        source: File object (upload) or path
        columns: {column name in file: column name in the DataFrame}, in output order
        label: File name shown in error messages, e.g. 'tidsbokning.csv'
        reader: pd.read_csv or pd.read_excel
        **kwargs: Passed to the reader

    Raises:
        InputFileError: If the file can't be parsed or a required column is missing
    """
    if reader is pd.read_csv and not isinstance(source, (str, Path)):
        source = _decode_text(source)

    try:
        header = reader(source, nrows=0, **kwargs).columns
    except (ValueError, zipfile.BadZipFile, pd.errors.ParserError) as error:
        kind = 'an Excel' if reader is pd.read_excel else 'a CSV'
        raise InputFileError(f"{label} could not be read as {kind} file ({error}). "
                             f"Is this the right file / export?") from error
    missing = [name for name in columns if name not in header]
    if missing:
        raise InputFileError(
            f"{label} is missing column(s): {', '.join(missing)}. "
            f"Is this the right file / export?"
        )
    if hasattr(source, 'seek'):
        source.seek(0)

    df = reader(source, usecols=list(columns), **kwargs)
    return df[list(columns)].rename(columns=columns)


def _clean_sku(series: pd.Series) -> pd.Series:
    """SKUs as stripped strings (missing stays missing); also handles numeric SKUs."""
    return series.map(lambda sku: str(sku).strip() if pd.notna(sku) else sku)


def _to_number(series: pd.Series) -> pd.Series:
    """Numbers in English (12.50) or German (12,50) notation; invalid -> NaN."""
    return pd.to_numeric(series.astype(str).str.replace(',', '.', regex=False), errors='coerce')


def load_products(file_obj: BinaryIO) -> pd.DataFrame:
    """Load and format product catalog from WordPress export CSV.

    Args:
        file_obj: File object containing CSV data

    Returns:
        DataFrame with columns: ArticleNumber, ProductDescription, RegularPrice
    """
    df = _read_columns(file_obj, {
        'SKU': 'ArticleNumber',
        'Short description': 'ProductDescription',
        'Regular price': 'RegularPrice',
    }, 'wc-product-export.csv')
    df['ArticleNumber'] = _clean_sku(df['ArticleNumber'])
    return df


def load_orders(file_obj: BinaryIO) -> pd.DataFrame:
    """Load and format orders from WooCommerce export Excel file.

    Performs email normalization and packing category key creation.

    Args:
        file_obj: File object containing Excel data

    Returns:
        DataFrame with normalized columns and PackingCategoryKey added
    """
    df = _read_columns(file_obj, {
        'Order Number': 'OrderNumber',
        'Full Name (Billing)': 'FullName',
        'Email (Billing)': 'Email',
        'Order Total Amount (- Refund)': 'OrderTotalAmount',
        'Order Date': 'OrderDate',
        'Customer Note': 'CustomerNote',
        'Phone (Billing)': 'PhoneOrder',
        'SKU': 'ArticleNumber',
        'Quantity (- Refund)': 'Quantity',
        'Product Name': 'ProductName',
        'Item Cost (inc. tax)': 'ItemCost',
        'Item #': 'ItemID',
        'Info': 'Info',
        'pa_packn_kategori': 'PackingCategory',
    }, 'orders.xlsx', reader=pd.read_excel)

    df['ArticleNumber'] = _clean_sku(df['ArticleNumber'])

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

    Invalid or missing dates/times become NaT and are reported by validation
    as incomplete timeslots.

    Args:
        file_obj: File object containing CSV data

    Returns:
        DataFrame with columns: OrderTime, Email, PickUpDate, PickUpTime,
                                PickUpDateTime, FullNameTimeslot, Telephone
    """
    df = _read_columns(file_obj, {
        'Time': 'OrderTime',
        'Email': 'Email',
        'app_date_1': 'PickUpDate',
        'app_slot_1': 'PickUpTime',
        'Select Date and Time': 'PickUpDateTime',
        'Name': 'FullNameTimeslot',
        'Telefon': 'Telephone',
    }, 'tidsbokning.csv', index_col=False,
        # Text columns as text: an all-empty column would otherwise be read as
        # float, and phone numbers would lose their leading zero
        dtype={name: str for name in ['Email', 'app_slot_1', 'Select Date and Time',
                                      'Name', 'Telefon']})

    df['OrderTime'] = pd.to_datetime(df['OrderTime'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    df['PickUpDate'] = pd.to_datetime(df['PickUpDate'], format='%Y-%m-%d', errors='coerce')
    # "Select Date and Time" has extra data after date and time; parse the first two parts
    df['PickUpDateTime'] = pd.to_datetime(
        df['PickUpDateTime'].str.split(' ').str[:2].str.join(' '),
        format='%Y-%m-%d %H:%M',
        errors='coerce'
    )
    # Pick-up time as datetime.time (NaT if missing/invalid)
    df['PickUpTime'] = df['PickUpTime'].map(_parse_time)

    # Convert emails to lowercase for matching
    df['Email'] = df['Email'].str.lower()

    return df


def _parse_time(value):
    """'HH:MM' -> datetime.time; anything else -> NaT."""
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), '%H:%M').time()
        except ValueError:
            pass
    return pd.NaT


def load_packing_categories(template_path: Path) -> pd.DataFrame:
    """Load packing categories (placeringsnycklar_<market>.xlsx).

    Args:
        template_path: Path to the market's packing categories file

    Returns:
        DataFrame with columns: PickUpArea, PackingCategory, PackingCategoryKey,
                                PackingCategoryIndex
    """
    df = _read_columns(str(template_path), {
        'info till Packlistan': 'PickUpArea',
        'Packningskategori': 'PackingCategory',
    }, Path(template_path).name, reader=pd.read_excel, header=1)

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

    Rows without day or time (e.g. blank separator rows) are ignored.

    Args:
        template_path: Path to the market's schedule file

    Returns:
        DataFrame with columns: Dag, Tid, Date, DateTime
    """
    df = _read_columns(str(template_path), {'Dag': 'Dag', 'Tid': 'Tid'},
                       Path(template_path).name, reader=pd.read_excel)
    df = df.dropna(subset=['Dag', 'Tid']).reset_index(drop=True)

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
    columns = ['SKU', 'Name', 'Regular price', 'Stock', 'Tax status', 'Tax class']
    df = _read_columns(file_obj, {c: c for c in columns}, 'wc-product-export.csv')
    df['SKU'] = _clean_sku(df['SKU'])
    df['Regular price'] = _to_number(df['Regular price'])
    return df


def load_products_report_export(file_obj: BinaryIO) -> pd.DataFrame:
    """Load product sales report from wc-products-report-export.csv for inventory report.

    Args:
        file_obj: File object containing CSV data

    Returns:
        DataFrame with columns: Product title, SKU, Items sold, N. Revenue, Category, Stock
    """
    columns = ['Product title', 'SKU', 'Items sold', 'N. Revenue', 'Category', 'Stock']
    df = _read_columns(file_obj, {c: c for c in columns}, 'wc-products-report-export.csv')
    df['SKU'] = _clean_sku(df['SKU'])
    df['Items sold'] = _to_number(df['Items sold'])
    return df


def load_sku_mapping(template_dir: Path) -> pd.DataFrame:
    """Load SKU prefix to sales area mapping from template file.

    Args:
        template_dir: Path to templates directory

    Returns:
        DataFrame with columns: SKU_Prefix, Sales_Area
    """
    template_path = template_dir / config.TEMPLATE_FILENAME_SKU_MAPPING
    return pd.read_excel(str(template_path), sheet_name='Mapping')
