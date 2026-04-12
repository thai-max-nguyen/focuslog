from tracker.analytics import compute_daily_summary


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
