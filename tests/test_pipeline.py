"""Tests for the UI-independent pipelines in src/pipeline.py."""

import io
import zipfile

import pytest

from src import config
from src.pipeline import (
    OrderInputs,
    build_diffs_report,
    build_lagerrapport,
    build_order_reports,
    load_order_inputs,
    prepare_inventory,
    validate_order_inputs,
    zip_reports,
)


@pytest.fixture(scope='module')
def pask_inputs(pask_data):
    return OrderInputs(
        market_type=config.MARKET_TYPE_PASK, products=pask_data.products,
        orders=pask_data.orders, timeslots=pask_data.timeslots,
        packing=pask_data.packing, schedule=pask_data.schedule,
    )


def test_load_order_inputs_from_uploads(pask_fixtures_dir, templates_dir):
    with open(pask_fixtures_dir / 'wc-product-export.csv', 'rb') as p, \
         open(pask_fixtures_dir / 'orders.xlsx', 'rb') as o, \
         open(pask_fixtures_dir / 'tidsbokning.csv', 'rb') as t:
        inputs = load_order_inputs(p, o, t, config.MARKET_TYPE_PASK, templates_dir)
    assert inputs.market_type == config.MARKET_TYPE_PASK
    assert len(inputs.orders) > 0 and len(inputs.schedule) > 0


def test_build_order_reports_pask(pask_inputs, templates_dir):
    progress = []
    reports = build_order_reports(pask_inputs, templates_dir,
                                  progress=lambda pct, msg: progress.append(pct))

    assert list(reports) == [
        config.OUTPUT_FILENAME_PACKLISTA,
        config.OUTPUT_FILENAME_HAMTNINGSLISTA,
        config.OUTPUT_FILENAME_SEMLELISTA,
        config.OUTPUT_FILENAME_MASTERLISTA,
        config.OUTPUT_FILENAME_ALLDATA,
    ]
    assert all(data[:2] == b'PK' for data in reports.values()), "xlsx = zip container"
    assert progress == sorted(progress) and progress[-1] == 100


def test_semlelista_only_for_pask(pask_inputs, templates_dir):
    from dataclasses import replace
    reports = build_order_reports(replace(pask_inputs, market_type=config.MARKET_TYPE_JULMARKNAD),
                                  templates_dir)
    assert config.OUTPUT_FILENAME_SEMLELISTA not in reports


def test_runs_are_isolated(pask_inputs, templates_dir):
    """Two runs return independent results; nothing is shared via disk."""
    first = build_order_reports(pask_inputs, templates_dir)
    second = build_order_reports(pask_inputs, templates_dir)
    assert first is not second
    assert set(first) == set(second)


def test_zip_contains_exactly_given_reports(pask_inputs, templates_dir):
    diffs = build_diffs_report(validate_order_inputs(pask_inputs))
    reports = build_order_reports(pask_inputs, templates_dir)

    data = zip_reports({**diffs, **reports})

    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert names == [config.OUTPUT_FILENAME_DIFFS, *reports]


def test_inventory_pipeline(pask_fixtures_dir, templates_dir):
    with open(pask_fixtures_dir / 'wc-product-export.csv', 'rb') as e, \
         open(pask_fixtures_dir / 'wc-products-report-export.csv', 'rb') as r:
        result = prepare_inventory(e, r, templates_dir)
    reports = build_lagerrapport(result.inventory, templates_dir)
    assert list(reports) == [config.OUTPUT_FILENAME_LAGERRAPPORT]
    assert 'warnings' in result.validation
