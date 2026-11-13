"""Golden-master (characterization) tests.

Every report generated from the obfuscated pask fixture must match the
committed snapshot in tests/golden/. This pins the current behavior so
refactors can prove they change nothing. See golden_master.py for how to
regenerate snapshots after an intended change.
"""

import os
from datetime import datetime

import pytest

from src import config, report_generator
from src.data_validator import generate_diffs_report, validate_data

from .golden_master import diff_snapshots, load_golden, save_golden, snapshot_workbook

UPDATE = os.environ.get('UPDATE_GOLDEN') == '1'
FROZEN_NOW = datetime(2026, 1, 1, 12, 0, 0)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FROZEN_NOW


@pytest.fixture
def frozen_clock(monkeypatch):
    """hämtningslista stamps datetime.now() into a cell; freeze it."""
    monkeypatch.setattr(report_generator, 'datetime', _FrozenDatetime)


def _build(name, out, data, inventory, templates_dir):
    if name == 'packlista':
        report_generator.generate_packlista(
            data.all_data, templates_dir, out, config.MARKET_TYPE_PASK)
    elif name == 'hamtningslista':
        report_generator.generate_hamtningslista(
            data.all_data, data.schedule, templates_dir, out)
    elif name == 'semlelista':
        report_generator.generate_semlelista(data.all_data, templates_dir, out)
    elif name == 'masterlista':
        report_generator.generate_masterlista(data.all_data, out)
    elif name == 'diffs':
        result = validate_data(data.orders, data.timeslots, data.products, data.packing)
        generate_diffs_report(result, out)
    elif name == 'lagerrapport':
        report_generator.generate_lagerrapport(inventory.inventory, templates_dir, out)
    else:
        raise ValueError(name)


@pytest.mark.parametrize('name', [
    'packlista', 'hamtningslista', 'semlelista', 'masterlista', 'diffs', 'lagerrapport',
])
def test_report_matches_golden(name, pask_data, pask_inventory, templates_dir,
                               tmp_path, frozen_clock):
    out = tmp_path / f'{name}.xlsx'
    _build(name, out, pask_data, pask_inventory, templates_dir)
    actual = snapshot_workbook(out)

    if UPDATE:
        save_golden(name, actual)
        pytest.skip(f'golden snapshot {name}.json updated')

    diffs = diff_snapshots(load_golden(name), actual)
    assert not diffs, f'{name} differs from golden snapshot:\n' + '\n'.join(diffs)
