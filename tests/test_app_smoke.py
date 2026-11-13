"""Smoke tests for the Streamlit UI (app.py) using streamlit.testing.

These run the real script headlessly: authentication gate and initial render.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / 'app.py')
PASSWORD = 'test-password'


@pytest.fixture
def app():
    at = AppTest.from_file(APP, default_timeout=30)
    at.secrets['password'] = PASSWORD
    return at.run()


def test_shows_only_password_prompt_before_login(app):
    assert not app.exception
    assert len(app.text_input) == 1
    assert app.text_input[0].label == 'Password'
    assert len(app.title) == 0


def test_wrong_password_shows_error(app):
    app.text_input[0].input('wrong').run()
    assert not app.exception
    assert any('incorrect' in e.value for e in app.error)
    assert len(app.title) == 0


def test_correct_password_renders_main_ui(app):
    app.text_input[0].input(PASSWORD).run()
    assert not app.exception
    assert app.title[0].value.startswith('📊 WebShop Report Generator')
    assert len(app.tabs) == 2
    assert app.selectbox[0].options == ['Julmarknad', 'Julmaten', 'Påskmarknad']


def test_non_ascii_password_does_not_crash(app):
    """hmac.compare_digest rejects non-ASCII str; passwords are compared as bytes."""
    app.text_input[0].input('lösenord').run()
    assert not app.exception
    assert any('incorrect' in e.value for e in app.error)


def test_non_ascii_password_can_be_correct():
    at = AppTest.from_file(APP, default_timeout=30)
    at.secrets['password'] = 'påsk-å'
    at.run()
    at.text_input[0].input('påsk-å').run()
    assert not at.exception
    assert len(at.tabs) == 2


def test_missing_password_secret_shows_clear_error():
    # Empty value: AppTest would otherwise fall back to a local secrets.toml
    at = AppTest.from_file(APP, default_timeout=30)
    at.secrets['password'] = ''
    at.run()
    assert not at.exception
    assert any('not configured' in e.value for e in at.error)


FIXTURES = Path(__file__).parent / 'fixtures' / 'pask'
XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
# uploader label -> (fixture file, mime type)
UPLOADS = {
    'Products (CSV)': ('wc-product-export.csv', 'text/csv'),
    'Orders (Excel)': ('orders.xlsx', XLSX),
    'Time Slots (CSV)': ('tidsbokning.csv', 'text/csv'),
}


def _button(at, label_start):
    return next(b for b in at.button if b.label.startswith(label_start))


def _download_labels(at):
    return [d.proto.label for d in at.get('download_button')]


@pytest.mark.slow
def test_order_workflow_end_to_end():
    at = AppTest.from_file(APP, default_timeout=120)
    at.secrets['password'] = PASSWORD
    at.run()
    at.text_input[0].input(PASSWORD).run()

    at.selectbox[0].select('pask').run()
    for uploader in at.file_uploader:
        if uploader.label in UPLOADS:
            name, mime = UPLOADS[uploader.label]
            uploader.set_value((name, (FIXTURES / name).read_bytes(), mime))
    at.run()
    assert not at.exception

    _button(at, '▶️ Run Validation').click().run()
    assert not at.exception
    assert any('Validation Results' in s.value for s in at.subheader)
    assert any('order lines from 10 orders' in w.value for w in at.warning)

    _button(at, '🚀 Generate All Reports').click().run()
    assert not at.exception
    labels = _download_labels(at)
    assert '📦 Download All Reports (ZIP)' in labels
    assert '📥 Semlelista (Semla List)' in labels

    # Changing the market invalidates validation and generated reports
    at.selectbox[0].select('julmarknad').run()
    assert not at.exception
    assert not any('Validation Results' in s.value for s in at.subheader)
    assert '📦 Download All Reports (ZIP)' not in _download_labels(at)
