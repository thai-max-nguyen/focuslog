import pytest
import os
import tempfile
from tracker.db import Database


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    database = Database(path)
    database.init()
    yield database
    database.close()
    os.unlink(path)


def test_init_creates_tables(db):
    tables = db.get_tables()
    assert "sessions" in tables
    assert "daily_summary" in tables
    assert "rules" in tables


def test_insert_session(db):
    session_id = db.insert_session(
        app_name="VSCode",
        window_title="main.py — focuslog",
        category="Work",
        start_time=1700000000,
        end_time=1700000300,
        duration=300,
        is_idle=False
    )
    assert session_id > 0


def test_get_sessions_by_date(db):
    db.insert_session(
        app_name="VSCode",
        window_title="test.py",
        category="Work",
        start_time=1700000000,
        end_time=1700000300,
        duration=300,
        is_idle=False
    )
    sessions = db.get_sessions_by_date("2023-11-14")
    assert len(sessions) == 1
    assert sessions[0]["app_name"] == "VSCode"


def test_insert_rule(db):
    db.insert_rule(app_name="YouTube", url_contains=None, category="Entertainment")
    rules = db.get_rules()
    assert any(r["app_name"] == "YouTube" for r in rules)


def test_delete_rule(db):
    rule_id = db.insert_rule(app_name="Netflix", url_contains=None, category="Entertainment")
    db.delete_rule(rule_id)
    rules = db.get_rules()
    assert not any(r["app_name"] == "Netflix" for r in rules)
