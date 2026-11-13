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
    assert app.selectbox[0].options == ['julmarknad', 'julmaten', 'pask']


@pytest.mark.xfail(strict=True, reason="Known bug B7: hmac.compare_digest rejects "
                   "non-ASCII str -> TypeError. Fixed in Phase 1.")
def test_non_ascii_password_does_not_crash(app):
    app.text_input[0].input('lösenord').run()
    assert not app.exception
