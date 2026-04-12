import pytest
from unittest.mock import patch, MagicMock
from tracker.watcher import WindowWatcher


@pytest.fixture
def watcher():
    return WindowWatcher(poll_interval=1)


def test_get_active_window_returns_tuple(watcher):
    with patch("tracker.watcher.get_active_window_info") as mock:
        mock.return_value = ("VSCode", "main.py — focuslog")
        app, title = watcher._poll_once()
        assert app == "VSCode"
        assert "main.py" in title


def test_idle_detection(watcher):
    with patch("tracker.watcher.get_idle_seconds") as mock:
        mock.return_value = 400
        assert watcher.is_idle() is True

    with patch("tracker.watcher.get_idle_seconds") as mock:
        mock.return_value = 30
        assert watcher.is_idle() is False


def test_session_accumulates(watcher):
    with patch("tracker.watcher.get_active_window_info") as mock_win, \
         patch("tracker.watcher.get_idle_seconds") as mock_idle:
        mock_win.return_value = ("VSCode", "main.py")
        mock_idle.return_value = 0
        watcher._poll_once()
        assert watcher.current_app == "VSCode"
