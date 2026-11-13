"""Golden-master helpers: snapshot an .xlsx as JSON and diff two snapshots.

A snapshot captures, per sheet: every non-empty cell value and the merged
cell ranges. Formatting (fonts, fills) is intentionally not captured.

To regenerate snapshots after an *intended* output change:

    UPDATE_GOLDEN=1 pytest tests/test_golden_master.py

then review the JSON diff in git before committing.
"""

import json
from datetime import date, datetime, time
from pathlib import Path

import openpyxl

GOLDEN_DIR = Path(__file__).parent / 'golden'


def _serialize(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, (int, str, bool)):
        return value
    return str(value)


def snapshot_workbook(path: Path) -> dict:
    wb = openpyxl.load_workbook(path)
    return {
        sheet.title: {
            'cells': {
                cell.coordinate: _serialize(cell.value)
                for row in sheet.iter_rows()
                for cell in row
                if cell.value is not None
            },
            'merged': sorted(str(r) for r in sheet.merged_cells.ranges),
        }
        for sheet in wb.worksheets
    }


def diff_snapshots(expected: dict, actual: dict, limit: int = 20) -> list:
    """Return human-readable differences (at most `limit`)."""
    diffs = []
    if list(expected) != list(actual):
        missing = [s for s in expected if s not in actual]
        extra = [s for s in actual if s not in expected]
        diffs.append(f"sheets differ: missing={missing[:5]} extra={extra[:5]} "
                     f"(order equal: {sorted(expected) == sorted(actual)})")
    for sheet in expected:
        if sheet not in actual:
            continue
        exp, act = expected[sheet], actual[sheet]
        if exp['merged'] != act['merged']:
            diffs.append(f"[{sheet}] merged ranges differ")
        for coord in sorted(set(exp['cells']) | set(act['cells'])):
            e, a = exp['cells'].get(coord), act['cells'].get(coord)
            if e != a:
                diffs.append(f"[{sheet}] {coord}: expected {e!r}, got {a!r}")
            if len(diffs) >= limit:
                return diffs
    return diffs


def load_golden(name: str) -> dict:
    with open(GOLDEN_DIR / f'{name}.json', encoding='utf-8') as f:
        return json.load(f)


def save_golden(name: str, snapshot: dict) -> None:
    GOLDEN_DIR.mkdir(exist_ok=True)
    with open(GOLDEN_DIR / f'{name}.json', 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=0, sort_keys=False)
        f.write('\n')
