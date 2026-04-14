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


def test_init_creates_tag_tables(db):
    tables = db.get_tables()
    assert "session_tags" in tables
    assert "tag_skips" in tables


def test_upsert_tag_creates(db):
    sid = db.insert_session("Jira", "Ticket", "Work", 1700000000, 1700000500, 500, False)
    tag_id = db.upsert_tag(sid, "NFC review", "user", 0.9)
    assert tag_id > 0
    tag = db.get_tag(sid)
    assert tag is not None
    assert tag["task_label"] == "NFC review"
    assert tag["source"] == "user"
    assert abs(tag["confidence"] - 0.9) < 0.001


def test_upsert_tag_updates_existing(db):
    sid = db.insert_session("Jira", "Ticket", "Work", 1700000000, 1700000500, 500, False)
    db.upsert_tag(sid, "Old label", "user", 0.9)
    db.upsert_tag(sid, "New label", "suggested", 0.9)
    tag = db.get_tag(sid)
    assert tag["task_label"] == "New label"
    assert tag["source"] == "suggested"


def test_get_tag_returns_none_if_missing(db):
    sid = db.insert_session("Jira", "Ticket", "Work", 1700000000, 1700000500, 500, False)
    assert db.get_tag(sid) is None


def test_get_recent_tags(db):
    for i in range(6):
        sid = db.insert_session("App", "Title", "Work", 1700000000 + i * 600, 1700000500 + i * 600, 500, False)
        db.upsert_tag(sid, f"Task {i}", "user", 0.9)
    recent = db.get_recent_tags(limit=5)
    assert len(recent) == 5
    # Most recent first
    assert recent[0]["task_label"] == "Task 5"


def test_get_tags_for_app(db):
    sid1 = db.insert_session("Jira", "Board", "Work", 1700000000, 1700000500, 500, False)
    db.upsert_tag(sid1, "NFC review", "user", 0.9)
    sid2 = db.insert_session("Figma", "Design", "Work", 1700001000, 1700001500, 500, False)
    db.upsert_tag(sid2, "Figma task", "user", 0.9)

    tags = db.get_tags_for_app("Jira", days=30)
    labels = [t["task_label"] for t in tags]
    assert "NFC review" in labels
    assert "Figma task" not in labels


def test_get_top_tags(db):
    for _ in range(3):
        sid = db.insert_session("Jira", "T", "Work", 1700000000, 1700000500, 500, False)
        db.upsert_tag(sid, "Frequent task", "user", 0.9)
    sid = db.insert_session("Figma", "T", "Work", 1700001000, 1700001500, 500, False)
    db.upsert_tag(sid, "Rare task", "user", 0.9)
    top = db.get_top_tags(limit=5)
    assert top[0]["task_label"] == "Frequent task"


def test_get_all_tags(db):
    for i in range(3):
        sid = db.insert_session("App", "T", "Work", 1700000000 + i * 600, 1700000600 + i * 600, 600, False)
        db.upsert_tag(sid, f"Task {i}", "user", 0.9)
    all_tags = db.get_all_tags(limit=100)
    assert len(all_tags) == 3


def test_insert_skip(db):
    sid = db.insert_session("Jira", "T", "Work", 1700000000, 1700000500, 500, False)
    db.insert_skip(sid)
    # No assertion needed beyond no exception — skip is write-only in Phase 1


def test_get_sessions_by_date_with_tags(db):
    from datetime import datetime
    # Use local midnight — matches how get_sessions_by_date_with_tags parses the date string
    day_start = int(datetime.strptime("2024-01-15", "%Y-%m-%d").timestamp())

    # Tagged session
    sid1 = db.insert_session("Jira", "Board", "Work", day_start + 3600, day_start + 4200, 600, False)
    db.upsert_tag(sid1, "NFC review", "user", 0.9)
    # Untagged session (same day)
    sid2 = db.insert_session("Figma", "Design", "Work", day_start + 7200, day_start + 7800, 600, False)
    # Idle session — must be excluded
    db.insert_session("System", "Idle", "Unknown", day_start + 10800, day_start + 11400, 600, True)
    # Session on a different day — must be excluded
    db.insert_session("Chrome", "Other day", "Work", day_start + 90000, day_start + 90600, 600, False)

    results = db.get_sessions_by_date_with_tags("2024-01-15")
    assert len(results) == 2

    tagged = next(r for r in results if r["id"] == sid1)
    assert tagged["task_label"] == "NFC review"
    assert tagged["task_source"] == "user"

    untagged = next(r for r in results if r["id"] == sid2)
    assert untagged["task_label"] is None
