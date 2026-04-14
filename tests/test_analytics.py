from tracker.analytics import compute_daily_summary, resolve_session_context, compute_context_switches, aggregate_tasks


SAMPLE_SESSIONS = [
    {"app_name": "VSCode", "window_title": "main.py", "category": "Work",
     "start_time": 1700000000, "end_time": 1700001800, "duration": 1800, "is_idle": False},
    {"app_name": "Safari", "window_title": "twitter.com", "category": "Entertainment",
     "start_time": 1700001800, "end_time": 1700001830, "duration": 30, "is_idle": False},
    {"app_name": "VSCode", "window_title": "test.py", "category": "Work",
     "start_time": 1700001830, "end_time": 1700001950, "duration": 120, "is_idle": False},
]


def test_total_active_time():
    summary = compute_daily_summary(SAMPLE_SESSIONS)
    assert summary["total_active"] == 1950


def test_deep_work_detection():
    summary = compute_daily_summary(SAMPLE_SESSIONS)
    assert summary["deep_work"] == 1800


def test_distraction_count():
    summary = compute_daily_summary(SAMPLE_SESSIONS)
    assert summary["distractions"] >= 1


def test_productivity_score():
    summary = compute_daily_summary(SAMPLE_SESSIONS)
    expected = 1800 / 1950
    assert abs(summary["productivity_score"] - expected) < 0.01


def test_top_apps():
    summary = compute_daily_summary(SAMPLE_SESSIONS)
    assert summary["top_apps"][0]["app_name"] == "VSCode"


def test_category_breakdown():
    summary = compute_daily_summary(SAMPLE_SESSIONS)
    assert "Work" in summary["categories"]
    assert summary["categories"]["Work"] == 1920


BASE_TIME = 1700000000

def _s(id, app, cat, start_offset, duration, tag=None):
    """Helper: build a session dict with optional tag."""
    end = BASE_TIME + start_offset + duration
    session = {
        "id": id,
        "app_name": app,
        "category": cat,
        "start_time": BASE_TIME + start_offset,
        "end_time": end,
        "duration": duration,
        "is_idle": 0,
        "task_label": tag,
        "task_source": "user" if tag else None,
        "task_confidence": 0.9 if tag else None,
    }
    return session


def test_user_tagged_session_has_confidence_09():
    sessions = [_s(1, "Jira", "Work", 0, 600, tag="NFC review")]
    resolved = resolve_session_context(sessions)
    assert resolved[0]["context_label"] == "NFC review"
    assert resolved[0]["context_confidence"] == 0.9
    assert resolved[0]["context_source"] == "user"


def test_untagged_inherits_previous_context():
    sessions = [
        _s(1, "Jira", "Work", 0, 600, tag="NFC review"),
        _s(2, "Figma", "Work", 600, 300),  # no tag, small gap
    ]
    resolved = resolve_session_context(sessions)
    assert resolved[1]["context_label"] == "NFC review"
    assert resolved[1]["context_confidence"] == 0.6
    assert resolved[1]["context_source"] == "inferred"


def test_no_inheritance_after_long_idle_gap():
    sessions = [
        _s(1, "Jira", "Work", 0, 600, tag="NFC review"),
        _s(2, "Figma", "Work", 1800, 300),  # 1200s gap (20 min > 10 min threshold)
    ]
    resolved = resolve_session_context(sessions)
    assert resolved[1]["context_label"] == "UNKNOWN"
    assert resolved[1]["context_confidence"] == 0.3


def test_no_inheritance_on_category_jump_to_entertainment():
    sessions = [
        _s(1, "Jira", "Work", 0, 600, tag="NFC review"),
        _s(2, "YouTube", "Entertainment", 600, 300),
    ]
    resolved = resolve_session_context(sessions)
    assert resolved[1]["context_label"] == "Entertainment"
    assert resolved[1]["context_source"] == "inferred_category"
    assert abs(resolved[1]["context_confidence"] - 0.55) < 0.001


def test_communication_gets_category_label():
    sessions = [_s(1, "Microsoft Teams", "Communication", 0, 300)]
    resolved = resolve_session_context(sessions)
    assert resolved[0]["context_label"] == "Communication"
    assert resolved[0]["context_source"] == "inferred_category"


def test_context_switch_counted():
    sessions = [
        _s(1, "Jira", "Work", 0, 600, tag="NFC review"),
        _s(2, "Jira", "Work", 600, 600, tag="Bug fix"),  # different task
    ]
    resolved = resolve_session_context(sessions)
    switches = compute_context_switches(resolved)
    assert switches == 1


def test_unknown_not_counted_as_switch():
    sessions = [
        _s(1, "Jira", "Work", 0, 600, tag="NFC review"),
        _s(2, "Figma", "Work", 1800, 600),  # long gap → UNKNOWN
        _s(3, "Jira", "Work", 2400, 600, tag="NFC review"),
    ]
    resolved = resolve_session_context(sessions)
    switches = compute_context_switches(resolved)
    # session 2 is UNKNOWN, should not count as switch
    assert switches == 0


def test_aggregate_tasks_groups_by_label():
    sessions = [
        _s(1, "Jira", "Work", 0, 600, tag="NFC review"),
        _s(2, "Figma", "Work", 600, 300, tag="NFC review"),
        _s(3, "Jira", "Work", 900, 600, tag="Bug fix"),
    ]
    resolved = resolve_session_context(sessions)
    tasks = aggregate_tasks(resolved)
    labels = [t["task_label"] for t in tasks]
    assert "NFC review" in labels
    assert "Bug fix" in labels
    nfc = next(t for t in tasks if t["task_label"] == "NFC review")
    assert nfc["total_duration"] == 900


def test_aggregate_tasks_uncategorized_last():
    sessions = [
        _s(1, "Jira", "Work", 0, 600, tag="NFC review"),
        _s(2, "Figma", "Work", 1800, 600),  # UNKNOWN → Uncategorized
    ]
    resolved = resolve_session_context(sessions)
    tasks = aggregate_tasks(resolved)
    assert tasks[-1]["task_label"] == "Uncategorized"
