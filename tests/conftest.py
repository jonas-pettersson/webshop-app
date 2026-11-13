"""Shared pytest fixtures for WebShop Report tests."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.data_loader import (
    load_orders,
    load_packing_categories,
    load_product_export,
    load_products,
    load_products_report_export,
    load_schedule,
    load_sku_mapping,
    load_timeslots,
)
from src.data_processor import merge_all_data, sort_for_reports
from src.data_validator import remove_duplicate_bookings
from src.lagerrapport_processor import prepare_lagerrapport_data
from src.markets import PASK


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / 'fixtures'


@pytest.fixture
def pask_fixtures_dir(fixtures_dir):
    """Return path to pask test fixtures."""
    return fixtures_dir / 'pask'


@pytest.fixture
def templates_dir():
    """Return path to templates directory."""
    return Path(__file__).parent.parent / 'templates'


@pytest.fixture
def pask_product_export_file(pask_fixtures_dir):
    """Return path to pask product export CSV."""
    return pask_fixtures_dir / 'wc-product-export.csv'


@pytest.fixture
def pask_orders_file(pask_fixtures_dir):
    """Return path to pask orders Excel file."""
    return pask_fixtures_dir / 'orders.xlsx'


@pytest.fixture
def pask_timeslots_file(pask_fixtures_dir):
    """Return path to pask timeslots CSV."""
    return pask_fixtures_dir / 'tidsbokning.csv'


@pytest.fixture
def pask_products_report_file(pask_fixtures_dir):
    """Return path to pask products report CSV."""
    return pask_fixtures_dir / 'wc-products-report-export.csv'


@pytest.fixture
def pask_packing_categories_file(pask_fixtures_dir):
    """Return path to pask packing categories template."""
    return pask_fixtures_dir / 'placeringsnycklar_pask.xlsx'


@pytest.fixture
def pask_schedule_file(pask_fixtures_dir):
    """Return path to pask schedule template."""
    return pask_fixtures_dir / 'schedule_pask.xlsx'


# ---------------------------------------------------------------------------
# Pre-loaded pask datasets (session-scoped: loaded once, treat as read-only)
# ---------------------------------------------------------------------------

_FIXTURES_PASK = Path(__file__).parent / 'fixtures' / 'pask'
_TEMPLATES = Path(__file__).parent.parent / 'templates'


@pytest.fixture(scope='session')
def pask_data():
    """All pask inputs loaded exactly as app.py loads them.

    Packing categories and schedule come from the fixture copies (not
    templates/) so that editing next season's templates doesn't change
    test inputs. Report *layout* templates come from templates/.
    """
    with open(_FIXTURES_PASK / 'wc-product-export.csv', 'rb') as f:
        products = load_products(f)
    with open(_FIXTURES_PASK / 'orders.xlsx', 'rb') as f:
        orders = load_orders(f)
    with open(_FIXTURES_PASK / 'tidsbokning.csv', 'rb') as f:
        timeslots = load_timeslots(f)
    packing = load_packing_categories(PASK.packing_categories(_FIXTURES_PASK))
    schedule = load_schedule(PASK.schedule(_FIXTURES_PASK))

    all_data = sort_for_reports(merge_all_data(
        orders, remove_duplicate_bookings(timeslots), products, packing
    ))
    return SimpleNamespace(
        products=products, orders=orders, timeslots=timeslots,
        packing=packing, schedule=schedule, all_data=all_data,
    )


@pytest.fixture(scope='session')
def pask_inventory():
    """Inventory (lagerrapport) inputs and processed data for pask."""
    with open(_FIXTURES_PASK / 'wc-product-export.csv', 'rb') as f:
        product_export = load_product_export(f)
    with open(_FIXTURES_PASK / 'wc-products-report-export.csv', 'rb') as f:
        products_report = load_products_report_export(f)
    sku_mapping = load_sku_mapping(_TEMPLATES)
    inventory = prepare_lagerrapport_data(product_export, products_report, sku_mapping)
    return SimpleNamespace(
        product_export=product_export, products_report=products_report,
        sku_mapping=sku_mapping, inventory=inventory,
    )
