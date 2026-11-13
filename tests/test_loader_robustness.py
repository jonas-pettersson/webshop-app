"""Loaders must cope with real-world export variations (or fail with a clear message)."""

import io
from datetime import time

import openpyxl
import pandas as pd
import pytest

from src.data_loader import (
    InputFileError,
    load_orders,
    load_product_export,
    load_products,
    load_schedule,
    load_timeslots,
)

TIMESLOT_HEADER = 'ID,Time,Email,app_date_1,app_slot_1,Select Date and Time,Name,Telefon\n'


def _csv(text: str, encoding='utf-8') -> io.BytesIO:
    return io.BytesIO(text.encode(encoding))


def test_reordered_columns_are_read_by_name():
    """WordPress may reorder export columns; values must not shift."""
    df = load_products(_csv('Regular price,Extra,SKU,Short description\n9.5,x,#A#,Kaka\n'))
    assert df.to_dict('records') == [
        {'ArticleNumber': '#A#', 'ProductDescription': 'Kaka', 'RegularPrice': 9.5}
    ]


def test_orders_with_reordered_columns(pask_fixtures_dir, pask_data):
    """Same orders file with its columns reversed loads to the same data."""
    original = pd.read_excel(pask_fixtures_dir / 'orders.xlsx')
    buffer = io.BytesIO()
    original[original.columns[::-1]].to_excel(buffer, index=False)
    buffer.seek(0)

    pd.testing.assert_frame_equal(load_orders(buffer), pask_data.orders)


def test_missing_column_names_the_column():
    with pytest.raises(InputFileError, match=r"tidsbokning\.csv is missing column\(s\): Telefon"):
        load_timeslots(_csv('Time,Email,app_date_1,app_slot_1,Select Date and Time,Name\n'))


def test_wrong_file_is_reported():
    """E.g. uploading the product export into the time slots field."""
    with pytest.raises(InputFileError, match='Is this the right file'):
        load_timeslots(_csv('SKU,Short description,Regular price\n#A#,Kaka,9.5\n'))


@pytest.mark.parametrize('encoding', ['utf-8', 'utf-8-sig', 'latin_1'])
def test_timeslots_encoding(encoding):
    row = '1,2026-03-12 10:00:00,a@x.se,2026-03-21,13:00,2026-03-21 13:00 1,Åsa Öberg,0660\n'
    df = load_timeslots(_csv(TIMESLOT_HEADER + row, encoding))
    assert df['FullNameTimeslot'].iloc[0] == 'Åsa Öberg'


def test_timeslots_invalid_and_empty_times_become_missing():
    rows = ('1,2026-03-12 10:00:00,a@x.se,2026-03-21,13:00,,A,1\n'
            '2,2026-03-12 10:00:00,b@x.se,2026-03-21,,,B,2\n'
            '3,2026-03-12 10:00:00,c@x.se,2026-03-21,25:99,,C,3\n'
            '4,2026-03-12 10:00:00,d@x.se,2026-03-21, 09:30 ,,D,4\n')
    df = load_timeslots(_csv(TIMESLOT_HEADER + rows))
    assert df['PickUpTime'].iloc[0] == time(13, 0)
    assert pd.isna(df['PickUpTime'].iloc[1])
    assert pd.isna(df['PickUpTime'].iloc[2])
    assert df['PickUpTime'].iloc[3] == time(9, 30)


def test_timeslots_with_all_times_empty():
    """An all-empty column is parsed as float by pandas; must not crash."""
    rows = '1,2026-03-12 10:00:00,a@x.se,2026-03-21,,,A,1\n'
    df = load_timeslots(_csv(TIMESLOT_HEADER + rows))
    assert df['PickUpTime'].isna().all()


def test_skus_are_stripped_and_numeric_skus_work():
    products = load_products(_csv('SKU,Short description,Regular price\n #A# ,x,1\n12345,y,2\n'))
    assert list(products['ArticleNumber']) == ['#A#', '12345']

    export = load_product_export(_csv(
        'SKU,Name,Regular price,Stock,Tax status,Tax class\n12345,y,"2,50",1,taxable,\n'))
    assert export['SKU'].iloc[0] == '12345'
    assert export['Regular price'].iloc[0] == 2.5


def test_schedule_ignores_blank_rows(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Dag', 'Tid'])
    ws.append([pd.Timestamp('2026-03-21').to_pydatetime(), time(13, 0)])
    ws.append([None, None])
    ws.append([pd.Timestamp('2026-03-22').to_pydatetime(), time(10, 0)])
    path = tmp_path / 'schedule_test.xlsx'
    wb.save(path)

    df = load_schedule(path)
    assert len(df) == 2
    assert list(df['Tid']) == [time(13, 0), time(10, 0)]


def test_timeslot_phone_numbers_keep_leading_zero():
    rows = '1,2026-03-12 10:00:00,a@x.se,2026-03-21,13:00,,A,06601234567\n'
    df = load_timeslots(_csv(TIMESLOT_HEADER + rows))
    assert df['Telephone'].iloc[0] == '06601234567'


def test_csv_uploaded_as_excel_is_reported():
    with pytest.raises(InputFileError, match=r'orders\.xlsx could not be read as an Excel file'):
        load_orders(_csv('SKU,Short description\n#A#,Kaka\n'))
