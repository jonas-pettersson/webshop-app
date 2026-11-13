"""Edge cases that used to drop orders silently or crash report generation.

Policy: data problems produce validation warnings, but every order that
can be matched still appears in the reports (never silently dropped).
"""

import io
from datetime import time

import openpyxl
import pandas as pd
import pytest

from src import config
from src.data_loader import load_packing_categories
from src.data_validator import remove_duplicate_bookings
from src.excel_utils import set_cell_value
from src.markets import MARKETS, PASK
from src.report_generator import (
    SLOT_LABEL_NO_TIME,
    generate_hamtningslista,
    generate_masterlista,
    generate_packlista,
    generate_semlelista,
)


def _workbook(data: bytes):
    return openpyxl.load_workbook(io.BytesIO(data))


def _all_values(wb):
    return [c.value for ws in wb.worksheets for row in ws.iter_rows() for c in row]


@pytest.fixture
def broken_data(pask_data):
    """Fixture data with one order each: off-schedule, no time, no date, formula note."""
    df = pask_data.all_data.copy()
    orders = list(dict.fromkeys(df['OrderNumber']))
    semla_order = df.loc[df['ArticleNumber'] == config.ARTICLE_NUMBER_SEMLA, 'OrderNumber'].iloc[0]
    others = [o for o in orders if o != semla_order]
    cases = {
        'off_schedule': others[0],
        'no_time': semla_order,          # also exercises semlelista without time
        'no_date': others[1],
        'formula_note': others[2],
        'no_area': others[3],
    }
    df.loc[df['OrderNumber'] == cases['off_schedule'], 'PickUpTime'] = time(23, 59)
    df.loc[df['OrderNumber'] == cases['no_time'], 'PickUpTime'] = pd.NaT
    df.loc[df['OrderNumber'] == cases['no_date'], 'PickUpDate'] = pd.NaT
    df.loc[df['OrderNumber'] == cases['formula_note'], 'CustomerNote'] = '=1+1'
    first_line = df.index[df['OrderNumber'] == cases['no_area']][0]
    df.loc[first_line, 'PickUpArea'] = None
    return df, cases


def test_packlista_keeps_every_order(broken_data, templates_dir):
    df, cases = broken_data
    wb = _workbook(generate_packlista(df, PASK.packlista_template(templates_dir)))

    assert set(wb.sheetnames) == {f'PO_{o}' for o in df['OrderNumber'].unique()}

    # Line without pickup area is still listed
    no_area_sheet = wb[f"PO_{cases['no_area']}"]
    articles = {c.value for row in no_area_sheet.iter_rows() for c in row}
    expected = set(df.loc[df['OrderNumber'] == cases['no_area'], 'ArticleNumber'])
    assert expected <= articles


def test_hamtningslista_keeps_every_order(broken_data, pask_data, templates_dir):
    df, cases = broken_data
    wb = _workbook(generate_hamtningslista(df, pask_data.schedule, templates_dir))
    values = _all_values(wb)

    assert set(df['OrderNumber']) <= set(values), "every order must be on a pickup list"
    assert '23:59 (ej i schema)' in values
    assert SLOT_LABEL_NO_TIME in values
    assert 'Hämtas utan datum' in wb.sheetnames
    assert wb.sheetnames[-1] == 'Hämtas utan datum'


def test_hamtningslista_unchanged_slots_when_all_scheduled(pask_data, templates_dir):
    """No extra slots appear when every booking is in the schedule."""
    wb = _workbook(generate_hamtningslista(pask_data.all_data, pask_data.schedule, templates_dir))
    values = [v for v in _all_values(wb) if isinstance(v, str)]
    assert not any('ej i schema' in v for v in values)
    assert SLOT_LABEL_NO_TIME not in values


def test_semlelista_handles_missing_time(broken_data, templates_dir):
    df, cases = broken_data
    wb = _workbook(generate_semlelista(df, templates_dir))
    values = _all_values(wb)
    assert cases['no_time'] in values
    assert SLOT_LABEL_NO_TIME in values


def test_semlelista_without_semla_orders(pask_data, templates_dir):
    df = pask_data.all_data[pask_data.all_data['ArticleNumber'] != config.ARTICLE_NUMBER_SEMLA]
    wb = _workbook(generate_semlelista(df, templates_dir))
    assert wb.sheetnames == ['Semla-Lista']


class TestFormulaInjection:
    """Customer-entered text starting with '=' must stay text."""

    def _formula_cells(self, wb):
        return [c.coordinate for ws in wb.worksheets for row in ws.iter_rows()
                for c in row if c.data_type == 'f']

    def test_template_reports(self, broken_data, pask_data, templates_dir):
        df, _ = broken_data
        for data in (
            generate_packlista(df, PASK.packlista_template(templates_dir)),
            generate_hamtningslista(df, pask_data.schedule, templates_dir),
        ):
            wb = _workbook(data)
            assert '=1+1' in _all_values(wb)
            assert not self._formula_cells(wb)

    def test_dataframe_reports(self, broken_data):
        df, _ = broken_data
        wb = _workbook(generate_masterlista(df))
        assert '=1+1' in _all_values(wb)
        assert not self._formula_cells(wb)

    def test_set_cell_value(self):
        ws = openpyxl.Workbook().active
        set_cell_value(ws['A1'], '=HYPERLINK("http://evil","x")')
        set_cell_value(ws['A2'], float('nan'))
        set_cell_value(ws['A3'], pd.NaT)
        set_cell_value(ws['A4'], '+43 660 123')
        assert ws['A1'].data_type == 's'
        assert ws['A2'].value is None and ws['A3'].value is None
        assert ws['A4'].value == '+43 660 123'


def test_packing_templates_have_no_blank_or_duplicate_keys(templates_dir):
    for market in MARKETS.values():
        df = load_packing_categories(market.packing_categories(templates_dir))
        assert 'nan' not in set(df['PackingCategoryKey']), market
        assert not df['PackingCategoryKey'].duplicated().any(), market
        assert df['PackingCategoryIndex'].is_monotonic_increasing, market


def test_remove_duplicate_bookings_keeps_all_bookings_without_email():
    df = pd.DataFrame({'Email': ['a@x.se', 'a@x.se', None, None]})
    assert list(remove_duplicate_bookings(df).index) == [0, 2, 3]


def test_sorting_with_missing_dates_and_times(broken_data, pask_data):
    """CLAUDE.md 'Known Issue': sorting must not fail on missing dates/times."""
    from src.data_processor import sort_for_reports
    from src.data_validator import validate_data

    df, cases = broken_data
    result = sort_for_reports(df)
    assert result['OrderNumber'].iloc[-1] in (cases['no_date'], cases['no_time'])

    timeslots = pask_data.timeslots.copy()
    timeslots.loc[timeslots.index[:3], 'Email'] = timeslots['Email'].iloc[3]  # duplicates
    timeslots.loc[timeslots.index[0], 'PickUpTime'] = pd.NaT
    timeslots.loc[timeslots.index[1], 'PickUpDate'] = pd.NaT
    validation = validate_data(pask_data.orders, timeslots, pask_data.products,
                               pask_data.packing, pask_data.schedule)
    assert len(validation.duplicate_bookings) == 4
    assert len(validation.incomplete_timeslots) == 2
