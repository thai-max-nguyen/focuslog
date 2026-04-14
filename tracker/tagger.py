"""
tracker/tagger.py

System app filtering, suggestion engine, and popup trigger logic.
"""
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from tracker.db import Database

# Apps that macOS reports as active but represent system/non-user activity.
# Filtered at insert time — never stored in DB, never trigger popups.
SYSTEM_APP_BLOCKLIST: frozenset[str] = frozenset({
    "loginwindow",
    "usernotificationcenter",
    "systemuiserver",
    "dock",
    "universalaccessd",
    "controlcentre",
    "notificationcentre",
})


def is_system_app(app_name: str) -> bool:
    """Return True if app_name represents system activity, not user work."""
    return app_name.lower() in SYSTEM_APP_BLOCKLIST


_STOP_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
    "of", "is", "it", "be", "was", "are", "by", "with", "from", "as",
})


def get_suggestions(db: "Database", app_name: str, window_title: str) -> list[str]:
    """
    Return up to 4 suggested task labels for a session, in priority order:
      1. Recent tags (last 5 sessions — strongest recency signal)
      2. Past tags for same app (frequency × recency weighted)
      3. Window title keyword match (token overlap with past labels)
      4. Global top tags (fallback when history is sparse)
    """
    suggestions: list[str] = []
    seen: set[str] = set()

    def _add(label: str) -> None:
        label = label.strip()
        if label and label not in seen and len(suggestions) < 4:
            seen.add(label)
            suggestions.append(label)

    # Source 1: recent tags (any app)
    for row in db.get_recent_tags(limit=5):
        _add(row["task_label"])

    # Source 2: past tags for same app
    for row in db.get_tags_for_app(app_name, days=30)[:3]:
        _add(row["task_label"])

    # Source 3: window title keyword match
    if window_title:
        match = _title_keyword_match(db, window_title)
        if match:
            _add(match)

    # Source 4: global top tags fallback
    if len(suggestions) < 2:
        for row in db.get_top_tags(limit=4):
            _add(row["task_label"])

    return suggestions


def _title_keyword_match(db: "Database", window_title: str) -> Optional[str]:
    """Find the past task label whose tokens most overlap with the window title tokens."""
    tokens = {
        w.lower() for w in window_title.split()
        if w.lower() not in _STOP_WORDS and len(w) > 2
    }
    if not tokens:
        return None

    best_label: str | None = None
    best_overlap = 0
    for row in db.get_all_tags(limit=200):
        label_tokens = set(row["task_label"].lower().split())
        overlap = len(tokens & label_tokens)
        if overlap > best_overlap:
            best_overlap = overlap
            best_label = row["task_label"]

    return best_label if best_overlap >= 1 else None


class TriggerEngine:
    """
    In-memory popup trigger + cooldown state. Resets on FocusLog restart.
    Thread-safe: on_session_end runs in watcher thread, API callbacks run in uvicorn thread.
    """

    _COOLDOWN_STEPS = [20 * 60, 30 * 60, 45 * 60, 60 * 60]

    def __init__(self):
        import threading
        self._lock = threading.Lock()
        self._cooldown_until: float = 0.0
        self._consecutive_skips: int = 0
        self._active_session_ids: set[int] = set()
        self._started_at: float = time.time()

    def should_trigger(
        self,
        session_id: int,
        app_name: str,
        duration: int,
        prev_app_name: str = "",
    ) -> bool:
        if is_system_app(app_name):
            return False
        if duration < 3 * 60:
            return False
        # Relaxed threshold: 3–7 min only triggers if same app as previous session
        if duration < 7 * 60 and app_name != prev_app_name:
            return False
        with self._lock:
            if session_id in self._active_session_ids:
                return False
            if time.time() < self._cooldown_until:
                return False
        # Startup grace period: don't interrupt user in first 60 seconds
        if time.time() - self._started_at < 60:
            return False
        return True

    def record_open(self, session_id: int) -> None:
        """Call when popup is opened for a session."""
        with self._lock:
            self._active_session_ids.add(session_id)
            self._cooldown_until = time.time() + self._get_cooldown_seconds()

    def record_tag(self, session_id: int) -> None:
        """Call when user successfully tags a session — resets cooldown."""
        with self._lock:
            self._active_session_ids.discard(session_id)
            self._consecutive_skips = 0
            self._cooldown_until = 0.0

    def record_skip(self, session_id: int) -> None:
        """Call when user dismisses popup without tagging — escalates cooldown."""
        with self._lock:
            self._active_session_ids.discard(session_id)
            self._consecutive_skips = min(self._consecutive_skips + 1, 3)
            self._cooldown_until = time.time() + self._get_cooldown_seconds()

    def _get_cooldown_seconds(self) -> int:
        idx = min(self._consecutive_skips, len(self._COOLDOWN_STEPS) - 1)
        return self._COOLDOWN_STEPS[idx]
