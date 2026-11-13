"""Structural tests for report generation.

Cell-level content is pinned by test_golden_master.py; these tests check
the shape of each report (sheets, row counts, key columns).
"""

import openpyxl

from src import config
from src.markets import PASK
from src.report_generator import (
    generate_hamtningslista,
    generate_lagerrapport,
    generate_masterlista,
    generate_packlista,
    generate_semlelista,
)

EXCEL_ERROR_VALUES = {'#NULL!', '#DIV/0!', '#VALUE!', '#REF!', '#NAME?', '#NUM!', '#N/A'}


def test_packlista_one_sheet_per_order(pask_data, templates_dir, tmp_path):
    out = tmp_path / config.OUTPUT_FILENAME_PACKLISTA
    out.write_bytes(generate_packlista(pask_data.all_data, PASK.packlista_template(templates_dir)))

    wb = openpyxl.load_workbook(out)
    expected = {f'PO_{n}' for n in pask_data.all_data['OrderNumber'].unique()}
    assert set(wb.sheetnames) == expected
    assert 'template' not in wb.sheetnames


def test_hamtningslista_one_sheet_per_pickup_date(pask_data, templates_dir, tmp_path):
    out = tmp_path / config.OUTPUT_FILENAME_HAMTNINGSLISTA
    out.write_bytes(generate_hamtningslista(pask_data.all_data, pask_data.schedule, templates_dir))

    wb = openpyxl.load_workbook(out)
    expected = {f'Hämtas {d.date()}' for d in pask_data.all_data['PickUpDate'].unique()}
    assert set(wb.sheetnames) == expected


def test_semlelista_single_sheet_with_all_semla_lines(pask_data, templates_dir, tmp_path):
    out = tmp_path / config.OUTPUT_FILENAME_SEMLELISTA
    out.write_bytes(generate_semlelista(pask_data.all_data, templates_dir))

    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == ['Semla-Lista']

    semla_orders = set(
        pask_data.all_data.loc[
            pask_data.all_data['ArticleNumber'] == config.ARTICLE_NUMBER_SEMLA,
            'OrderNumber',
        ]
    )
    assert semla_orders, "fixture is expected to contain semla orders"
    sheet_values = {c.value for row in wb.active.iter_rows() for c in row}
    assert semla_orders <= sheet_values


def test_masterlista_one_row_per_order(pask_data, tmp_path):
    out = tmp_path / config.OUTPUT_FILENAME_MASTERLISTA
    out.write_bytes(generate_masterlista(pask_data.all_data))

    sheet = openpyxl.load_workbook(out).active
    assert sheet.max_row - 1 == pask_data.all_data['OrderNumber'].nunique()


def test_lagerrapport_rows_match_inventory(pask_inventory, templates_dir, tmp_path):
    out = tmp_path / config.OUTPUT_FILENAME_LAGERRAPPORT
    out.write_bytes(generate_lagerrapport(pask_inventory.inventory, templates_dir))

    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == ['Content']
    sheet = wb['Content']

    skus = [sheet.cell(row=r, column=1).value for r in range(2, sheet.max_row + 1)]
    assert skus == list(pask_inventory.inventory['SKU'])

    errors = [c.coordinate for row in sheet.iter_rows() for c in row
              if c.value in EXCEL_ERROR_VALUES]
    assert not errors, f"Excel error values in cells: {errors[:10]}"
