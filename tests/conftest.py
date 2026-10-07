"""Shared pytest fixtures for WebShop Report tests."""

from pathlib import Path
import pytest


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
    return pask_fixtures_dir / 'placeringsnycklar.xlsx'


@pytest.fixture
def pask_schedule_file(pask_fixtures_dir):
    """Return path to pask schedule template."""
    return pask_fixtures_dir / 'schedule.xlsx'
