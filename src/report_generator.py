"""Report generation for WebShop Report system.

Generates Excel reports from templates (see excel_utils.ReportTemplate):
- Packlista (packing lists per order)
- Hämtningslista (pickup schedules by date)
- Semlelista (semla orders by date and hour)
- Masterlista (master order list)
- Lagerrapport (inventory report)

Every generator returns the finished .xlsx as bytes.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from . import config
from .excel_utils import ReportTemplate, dataframe_to_xlsx_bytes

# Weekday names in Swedish
WEEKDAY_DICT = {
    0: 'Mån',
    1: 'Tis',
    2: 'Ons',
    3: 'Tor',
    4: 'Fre',
    5: 'Lör',
    6: 'Sön'
}

SLOT_LABEL_NOT_SCHEDULED = '{time:%H:%M} (ej i schema)'
SLOT_LABEL_NO_TIME = 'Ingen tid'

# Named ranges filled from the data (template name == DataFrame column)
PACKLISTA_HEADER_FIELDS = ['FullName', 'OrderTotalAmount', 'CustomerNote',
                           'OrderNumber', 'Telephone', 'PickUpDate', 'PickUpTime']
PACKLISTA_LINE_FIELDS = ['ArticleNumber', 'Quantity', 'ProductName', 'ItemCost', 'PickUpArea']
HAMTNINGSLISTA_ORDER_FIELDS = ['OrderNumber', 'FullName', 'Telephone',
                               'OrderTotalAmount', 'CustomerNote']
SEMLELISTA_HEADER_FIELDS = ['ArticleNumber', 'ProductName']
SEMLELISTA_ORDER_FIELDS = ['Quantity', 'OrderNumber', 'FullName', 'Email',
                           'PickUpDate', 'PickUpTime']

# Lagerrapport: template named range -> inventory DataFrame column
LAGERRAPPORT_FIELDS = {
    'SKU': 'SKU',
    'ProductTitle': 'Product title',
    'CategorySKUT': 'Category (SKUT)',
    'Category': 'Category',
    'RegularPrice': 'Regular price',
    'ItemsSold': 'Items sold',
    'Stock': 'Stock',
    'TaxClass': 'Tax class',
    'TotalSales': 'Total sales',
    'TotalTax': 'Total tax',
}

# Number of footer rows below the list whose heights are copied from the template
FOOTER_ROWS = 10


def _pickup_slots(scheduled_times, booked_times):
    """Time slots to print on one day's pickup list, as (time, header value).

    Every scheduled slot is printed (also when empty), in schedule order.
    Booked times that are not in the schedule are added, sorted into place
    and labelled "(ej i schema)", so no booking is left off the list.
    Bookings without a time come last under "Ingen tid" (time=None).
    Validation warns about both cases.
    """
    scheduled = list(scheduled_times)
    extra = sorted(set(booked_times.dropna()) - set(scheduled))

    slots = [(t, t) for t in scheduled]
    if extra:
        slots += [(t, SLOT_LABEL_NOT_SCHEDULED.format(time=t)) for t in extra]
        slots.sort(key=lambda slot: slot[0])
    if booked_times.isna().any():
        slots.append((None, SLOT_LABEL_NO_TIME))
    return slots


def generate_packlista(all_data_df: pd.DataFrame, template_path: Path) -> bytes:
    """Generate packing lists: one sheet per order, lines grouped by pickup area.

    Template layout: header fields, then an item row (named ranges of
    PACKLISTA_LINE_FIELDS), a separator row, then the footer.

    Args:
        all_data_df: Merged and sorted DataFrame
        template_path: The market's packlista template (MarketProfile.packlista_template)

    Returns:
        bytes: The .xlsx file content
    """
    tpl = ReportTemplate(template_path)
    item_row = tpl.row('ArticleNumber')
    separator_row = item_row + 1

    # Already sorted by pickup date/time. dropna=False: orders with missing
    # pickup date/time still get a list.
    for _, order in all_data_df.groupby(
        ['PickUpDate', 'PickUpTime', 'OrderNumber'], dropna=False
    ):
        first = order.iloc[0]
        sheet = tpl.new_sheet(f"PO_{first['OrderNumber']}")
        tpl.fill_many(sheet, first, PACKLISTA_HEADER_FIELDS)
        sheet.delete_rows(idx=item_row, amount=2)  # template item + separator row

        rows = 0        # rows inserted so far
        separators = 0  # of which separator rows (not numbered)

        # sort=False keeps the template's packing order
        for _, area_lines in order.groupby('PickUpArea', sort=False, dropna=False):
            for _, line in area_lines.iterrows():
                tpl.insert_row(sheet, item_row, item_row + rows)
                tpl.fill_many(sheet, line, PACKLISTA_LINE_FIELDS, row_offset=rows)
                tpl.fill(sheet, 'RowNumber', rows + 1 - separators, row_offset=rows)
                rows += 1

            tpl.insert_row(sheet, separator_row, item_row + rows)
            rows += 1
            separators += 1

        tpl.copy_row_heights(sheet, item_row + 2, item_row + rows, FOOTER_ROWS)
        tpl.fill(sheet, 'NumberOfRows', str(rows - separators))

    return tpl.to_bytes()


def generate_hamtningslista(
    all_data_df: pd.DataFrame,
    schedule_df: pd.DataFrame,
    template_dir: Path
) -> bytes:
    """Generate pickup lists: one sheet per pickup date, organized by time slot.

    Template layout: a slot header row (named range 'PickUpTime'), then an
    order row (HAMTNINGSLISTA_ORDER_FIELDS, 'RowNumber').

    Args:
        all_data_df: Merged and sorted DataFrame
        schedule_df: Schedule DataFrame with authorized pickup times
        template_dir: Path to templates directory

    Returns:
        bytes: The .xlsx file content
    """
    tpl = ReportTemplate(template_dir / config.TEMPLATE_FILENAME_HAMTLISTA)
    slot_row = tpl.row('PickUpTime')
    order_row = slot_row + 1

    # One sheet per date; missing date sorts last
    orders = all_data_df.drop_duplicates(subset=['OrderNumber'])
    for pickup_date, day_orders in orders.groupby('PickUpDate', dropna=False):
        has_date = pd.notna(pickup_date)

        sheet = tpl.new_sheet('Hämtas ' + (str(pickup_date.date()) if has_date else 'utan datum'))
        tpl.fill(sheet, 'Weekday', WEEKDAY_DICT[pickup_date.weekday()] if has_date else '')
        tpl.fill(sheet, 'PickUpDate', pickup_date.date() if has_date else None)
        tpl.fill(sheet, 'CreationDateTime', str(datetime.now()))
        sheet.delete_rows(idx=slot_row, amount=2)  # template slot + order row

        day_orders = day_orders.sort_values(by=['FullName'])
        scheduled_times = (
            schedule_df[schedule_df['Date'] == pickup_date.date()]['Tid'] if has_date else []
        )

        rows = 0          # rows inserted so far
        slot_headers = 0  # of which slot header rows (not numbered)

        for time, label in _pickup_slots(scheduled_times, day_orders['PickUpTime']):
            tpl.insert_row(sheet, slot_row, slot_row + rows)
            tpl.fill(sheet, 'PickUpTime', label, row_offset=rows)
            rows += 1
            slot_headers += 1

            if time is None:
                slot_orders = day_orders[day_orders['PickUpTime'].isna()]
            else:
                slot_orders = day_orders[day_orders['PickUpTime'] == time]

            # An empty slot still gets one (blank, numbered) row to write in
            for order in [row for _, row in slot_orders.iterrows()] or [None]:
                tpl.insert_row(sheet, order_row, slot_row + rows)
                # order fields are named on order_row, i.e. one row below slot_row
                if order is not None:
                    tpl.fill_many(sheet, order, HAMTNINGSLISTA_ORDER_FIELDS, row_offset=rows - 1)
                tpl.fill(sheet, 'RowNumber', rows + 1 - slot_headers, row_offset=rows - 1)
                rows += 1

    return tpl.to_bytes()


def generate_semlelista(all_data_df: pd.DataFrame, template_dir: Path) -> bytes:
    """Generate the semla list: semla orders grouped by date and hour.

    Template layout: an order row (SEMLELISTA_ORDER_FIELDS), then a summary
    row per hour ('Day', 'Hour', 'NumberOfItemsName', 'NumberOfItems').

    Args:
        all_data_df: Merged and sorted DataFrame
        template_dir: Path to templates directory

    Returns:
        bytes: The .xlsx file content
    """
    tpl = ReportTemplate(template_dir / config.TEMPLATE_FILENAME_SEMLELISTA)
    order_row = tpl.row('OrderNumber')
    summary_row = order_row + 1

    df_semla = all_data_df[all_data_df['ArticleNumber'] == config.ARTICLE_NUMBER_SEMLA].copy()
    # Missing time -> <NA>, grouped last as "Ingen tid"
    df_semla['PickUpHour'] = pd.array(
        [t.hour if pd.notna(t) else None for t in df_semla['PickUpTime']], dtype='Int64'
    )

    sheet = tpl.new_sheet('Semla-Lista')
    header = df_semla.iloc[0] if len(df_semla) > 0 else dict.fromkeys(SEMLELISTA_HEADER_FIELDS, '')
    tpl.fill_many(sheet, header, SEMLELISTA_HEADER_FIELDS)
    sheet.delete_rows(idx=order_row, amount=2)  # template order + summary row

    rows = 0
    for day, day_orders in df_semla.groupby('PickUpDate', dropna=False):
        for hour, hour_orders in day_orders.groupby('PickUpHour', dropna=False):
            for _, order in hour_orders.iterrows():
                tpl.insert_row(sheet, order_row, order_row + rows)
                tpl.fill_many(sheet, order, SEMLELISTA_ORDER_FIELDS, row_offset=rows)
                rows += 1

            # Summary row for this hour (its names sit one row below order_row)
            tpl.insert_row(sheet, summary_row, order_row + rows)
            offset = rows - 1
            tpl.fill(sheet, 'Day', day.strftime('%d.%m') if pd.notna(day) else 'Inget datum',
                     row_offset=offset)
            tpl.fill(sheet, 'Hour', f'{hour}:00 - {hour + 1}:00' if pd.notna(hour)
                     else SLOT_LABEL_NO_TIME, row_offset=offset)
            tpl.fill(sheet, 'NumberOfItemsName', 'Antal:', row_offset=offset)
            tpl.fill(sheet, 'NumberOfItems', hour_orders['Quantity'].sum(), row_offset=offset)
            rows += 2

        tpl.copy_row_heights(sheet, order_row + 2, order_row + rows, FOOTER_ROWS)

    return tpl.to_bytes()


def generate_masterlista(all_data_df: pd.DataFrame) -> bytes:
    """Generate master list: one row per order.

    Args:
        all_data_df: Merged and sorted DataFrame

    Returns:
        bytes: The .xlsx file content
    """
    df_master = all_data_df[[
        'OrderNumber', 'FullName', 'Email', 'OrderTotalAmount', 'OrderDate',
        'Telephone', 'CustomerNote', 'Info', 'PickUpDate', 'PickUpTime'
    ]].copy()

    df_master.columns = [
        'Order Number', 'Full Name (Billing)', 'Email (Billing)',
        'Order Total Amount', 'Order Date', 'Telephone', 'Customer Note',
        'Info ok', 'Hämtningsdag', 'Hämtning Tid'
    ]

    return dataframe_to_xlsx_bytes({'Sheet1': df_master.drop_duplicates()})


def generate_lagerrapport(inventory_df: pd.DataFrame, template_dir: Path) -> bytes:
    """Generate the inventory report: sheet 'Content', one row per product.

    Template layout: header row with named ranges (LAGERRAPPORT_FIELDS),
    then one formatted data row.

    Args:
        inventory_df: Output of lagerrapport_processor.prepare_lagerrapport_data()
        template_dir: Path to templates directory

    Returns:
        bytes: The .xlsx file content
    """
    tpl = ReportTemplate(template_dir / config.TEMPLATE_FILENAME_LAGERRAPPORT)
    header_row = tpl.row('SKU')
    data_row = header_row + 1

    sheet = tpl.new_sheet('Content')
    sheet.delete_rows(idx=data_row, amount=1)  # template data row

    for i, (_, product) in enumerate(inventory_df.iterrows()):
        tpl.insert_row(sheet, data_row, data_row + i)
        for name, column in LAGERRAPPORT_FIELDS.items():
            # named ranges are on the header row; data starts one row below
            tpl.fill(sheet, name, product[column], row_offset=i + 1)

    return tpl.to_bytes()
