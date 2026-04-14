"""
tracker/tagger.py

System app filtering, suggestion engine, and popup trigger logic.
"""
import logging
import re
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from tracker.db import Database

# Apps that macOS reports as active but represent system/non-user activity.
# Filtered at insert time — never stored in DB, never trigger popups.
_TICKET_RE = re.compile(r'\b([A-Za-z]+-\d+)\b')
_ACTIVE_CONTEXT_MAX_AGE     = 2 * 60 * 60  # 2h since last set
_ACTIVE_CONTEXT_IDLE_BREAK  = 30 * 60       # 30min without activity → expire
_ACTIVE_CONTEXT_MIN_CONF    = 0.7           # only boost if confidence ≥ this


class ActiveContext:
    """
    Tracks the most recently confirmed task label.

    Expires when:
      • > 2h have elapsed since the label was set, OR
      • > 30min have elapsed since the last recorded activity
        (notify_activity() is called each time a suggestion is requested,
         i.e. when the user switches to a new session).

    Only surfaced as a suggestion when the stored confidence ≥ 0.7.
    Low-confidence labels are hidden but NOT cleared, so they can recover
    if confidence is updated later.
    """

    def __init__(self) -> None:
        self._label: Optional[str] = None
        self._confidence: float = 0.0
        self._last_tag_time: float = 0.0
        self._last_activity_time: float = 0.0

    def set(self, label: str, confidence: float = 0.9) -> None:
        now = time.time()
        self._label = label
        self._confidence = confidence
        self._last_tag_time = now
        self._last_activity_time = now
        logging.debug("[active_context] set=%s conf=%.2f", label, confidence)

    def notify_activity(self) -> None:
        """Call when the user becomes active (tag saved, suggestion requested, etc.)."""
        if self._label:
            self._last_activity_time = time.time()

    def get(self) -> Optional[str]:
        """Return the active label if it passes confidence and expiry guards, else None."""
        if not self._label:
            return None
        now = time.time()
        age_expired  = (now - self._last_tag_time)      > _ACTIVE_CONTEXT_MAX_AGE
        idle_expired = (now - self._last_activity_time) > _ACTIVE_CONTEXT_IDLE_BREAK
        if age_expired or idle_expired:
            logging.debug("[active_context] expired label=%s", self._label)
            self._label = None
            return None
        if self._confidence < _ACTIVE_CONTEXT_MIN_CONF:
            # Hidden but not cleared — state is preserved for potential recovery.
            return None
        logging.debug("[active_context] used=%s", self._label)
        return self._label

    def clear(self) -> None:
        self._label = None


# Module-level singleton — call active_context.set(label) from api.py when a tag is saved.
active_context = ActiveContext()


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


def get_suggestions(
    db: "Database",
    app_name: str,
    window_title: str,
    active_ctx: Optional[str] = None,
) -> list[str]:
    """
    Return up to 4 suggested task labels for a session, in priority order:
      1. Active context (passed in, already validated by caller)
      2. Ticket ID extracted from window title (e.g. PROJ-123) — strong signal
      3. Recency cluster — last 3 unique labels, weighted by session duration
      4. Past tags for same app (frequency × recency weighted)
      5. Window title keyword match (token overlap with past labels)
      6. Global top tags (fallback when history is sparse)
    """
    suggestions: list[str] = []
    seen: set[str] = set()

    def _add(label: str, source: str, reason: str = "") -> None:
        label = label.strip()
        if not label or label in seen or len(suggestions) >= 4:
            return
        seen.add(label)
        suggestions.append(label)
        logging.debug("[suggestion] source=%s label=%s%s", source, label,
                      f" ({reason})" if reason else "")

    # Source 1: active context boost (confidence guard applied by caller via .get())
    if active_ctx:
        _add(active_ctx, "active_context")

    # Source 2: ticket ID from window title — strong, deterministic signal
    if window_title:
        ticket = _extract_ticket(window_title)
        if ticket:
            _add(ticket, "ticket", f"match={ticket}")

    # Source 3: recency cluster — last 3 unique labels weighted by session duration
    for row in db.get_recent_unique_tags(limit=3):
        _add(row["task_label"], "recency",
             f"score={row.get('decayed_duration', 0):.0f}s")

    # Source 4: past tags for same app
    for row in db.get_tags_for_app(app_name, days=30)[:3]:
        _add(row["task_label"], "app_history",
             f"app={app_name} freq={row.get('frequency', '?')}")

    # Source 5: window title keyword match
    if window_title and len(suggestions) < 4:
        match = _title_keyword_match(db, window_title)
        if match:
            _add(match, "keyword", f"title={window_title[:40]!r}")

    # Source 6: global top tags fallback
    if len(suggestions) < 2:
        for row in db.get_top_tags(limit=4):
            _add(row["task_label"], "fallback",
                 f"freq={row.get('frequency', '?')}")

    logging.debug("[suggestion] final=%s", suggestions)
    return suggestions


def _extract_ticket(window_title: str) -> Optional[str]:
    """
    Extract and normalize the first Jira-style ticket ID from a window title.
    Always returns uppercase (e.g. 'proj-123' → 'PROJ-123').
    """
    m = _TICKET_RE.search(window_title)
    return m.group(1).upper() if m else None


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
