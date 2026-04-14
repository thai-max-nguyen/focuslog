import pytest
import time
from tracker.tagger import is_system_app, SYSTEM_APP_BLOCKLIST


def test_loginwindow_is_system():
    assert is_system_app("loginwindow") is True


def test_usernotificationcenter_is_system():
    assert is_system_app("UserNotificationCenter") is True


def test_case_insensitive():
    assert is_system_app("LOGINWINDOW") is True
    assert is_system_app("Dock") is True


def test_real_apps_not_system():
    assert is_system_app("Jira") is False
    assert is_system_app("Microsoft Excel") is False
    assert is_system_app("Arc") is False
    assert is_system_app("Claude") is False


def test_blocklist_is_set():
    assert isinstance(SYSTEM_APP_BLOCKLIST, (set, frozenset))
    assert "loginwindow" in SYSTEM_APP_BLOCKLIST


import tempfile, os
from tracker.db import Database
from tracker.tagger import get_suggestions


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    database = Database(path)
    database.init()
    yield database
    database.close()
    os.unlink(path)


def test_get_suggestions_returns_list(db):
    result = get_suggestions(db, "Jira", "PCFUM sprint board")
    assert isinstance(result, list)
    assert len(result) <= 4


def test_recent_tags_appear_first(db):
    for i, label in enumerate(["Alpha", "Beta", "Gamma"]):
        sid = db.insert_session("App", "T", "Work", 1700000000 + i * 600, 1700000500 + i * 600, 500, False)
        db.upsert_tag(sid, label, "user", 0.9)
    suggestions = get_suggestions(db, "SomeOtherApp", "")
    assert "Gamma" in suggestions
    assert suggestions.index("Gamma") < suggestions.index("Alpha") if "Alpha" in suggestions else True


def test_same_app_tags_included(db):
    sid = db.insert_session("Jira", "Board", "Work", 1700000000, 1700000500, 500, False)
    db.upsert_tag(sid, "NFC review", "user", 0.9)
    suggestions = get_suggestions(db, "Jira", "Some unrelated title")
    assert "NFC review" in suggestions


def test_title_keyword_match(db):
    sid = db.insert_session("Figma", "Design", "Work", 1700000000, 1700000500, 500, False)
    db.upsert_tag(sid, "NFC onboarding", "user", 0.9)
    suggestions = get_suggestions(db, "Chrome", "NFC flow review - Figma")
    assert "NFC onboarding" in suggestions


def test_no_duplicates(db):
    sid = db.insert_session("Jira", "Board", "Work", 1700000000, 1700000500, 500, False)
    db.upsert_tag(sid, "My task", "user", 0.9)
    suggestions = get_suggestions(db, "Jira", "My task board")
    assert len(suggestions) == len(set(suggestions))


def test_global_fallback_when_no_history(db):
    for i in range(3):
        sid = db.insert_session("SomeApp", "T", "Work", 1700000000 + i * 600, 1700000500 + i * 600, 500, False)
        db.upsert_tag(sid, f"Global task {i}", "user", 0.9)
    suggestions = get_suggestions(db, "BrandNewApp", "")
    assert len(suggestions) >= 1


from tracker.tagger import TriggerEngine


def test_should_trigger_happy_path():
    engine = TriggerEngine()
    engine._started_at = time.time() - 120  # past startup grace period
    assert engine.should_trigger(session_id=1, app_name="Jira", duration=8 * 60, prev_app_name="Jira") is True


def test_should_not_trigger_system_app():
    engine = TriggerEngine()
    engine._started_at = time.time() - 120
    assert engine.should_trigger(session_id=1, app_name="loginwindow", duration=10 * 60, prev_app_name="") is False


def test_should_not_trigger_too_short():
    engine = TriggerEngine()
    engine._started_at = time.time() - 120
    assert engine.should_trigger(session_id=1, app_name="Jira", duration=100, prev_app_name="") is False


def test_three_minute_relaxed_threshold_requires_same_prev_app():
    engine = TriggerEngine()
    engine._started_at = time.time() - 120
    # 4 min, same app → trigger
    assert engine.should_trigger(session_id=1, app_name="Jira", duration=4 * 60, prev_app_name="Jira") is True
    # 4 min, different app → no trigger
    assert engine.should_trigger(session_id=2, app_name="Jira", duration=4 * 60, prev_app_name="Figma") is False


def test_cooldown_blocks_trigger():
    engine = TriggerEngine()
    engine._started_at = time.time() - 120
    engine.record_open(session_id=1)
    # Immediately after opening popup, cooldown is active
    assert engine.should_trigger(session_id=2, app_name="Jira", duration=8 * 60, prev_app_name="") is False


def test_record_tag_resets_cooldown():
    engine = TriggerEngine()
    engine._started_at = time.time() - 120
    engine.record_open(session_id=1)
    engine.record_tag(session_id=1)
    assert engine.should_trigger(session_id=2, app_name="Jira", duration=8 * 60, prev_app_name="") is True


def test_cooldown_escalates_on_skip():
    engine = TriggerEngine()
    assert engine._get_cooldown_seconds() == 20 * 60
    engine.record_open(1)
    engine.record_skip(1)
    assert engine._get_cooldown_seconds() == 30 * 60
    engine.record_open(2)
    engine.record_skip(2)
    assert engine._get_cooldown_seconds() == 45 * 60
    engine.record_open(3)
    engine.record_skip(3)
    assert engine._get_cooldown_seconds() == 60 * 60
    # Caps at 60 min
    engine.record_open(4)
    engine.record_skip(4)
    assert engine._get_cooldown_seconds() == 60 * 60


def test_startup_grace_period():
    engine = TriggerEngine()
    # _started_at is set to now() in __init__, so grace period active
    assert engine.should_trigger(session_id=1, app_name="Jira", duration=10 * 60, prev_app_name="") is False


def test_duplicate_session_not_triggered():
    engine = TriggerEngine()
    engine._started_at = time.time() - 120
    engine.record_open(session_id=42)
    assert engine.should_trigger(session_id=42, app_name="Jira", duration=10 * 60, prev_app_name="") is False
