"""
FocusLog — main entry point.
Starts the menu bar icon, window watcher, and FastAPI server.
"""
import json
import logging
import os
import threading
import webbrowser
from datetime import datetime

import rumps
import uvicorn

from tracker.api import create_app
from tracker.classifier import Classifier, DEFAULT_RULES
from tracker.db import Database
from tracker.tagger import is_system_app, TriggerEngine
from tracker.watcher import WindowWatcher

DATA_DIR = os.path.expanduser("~/Library/Application Support/focuslog")
RULES_PATH = os.path.join(DATA_DIR, "rules.json")
PORT = 7331

os.makedirs(DATA_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(os.path.join(DATA_DIR, "focuslog.log"))],
)
logger = logging.getLogger(__name__)


def load_rules() -> list[dict]:
    """Load rules.json and merge any new DEFAULT_RULES entries that are missing.

    User-created rules are never removed.  New default app-name rules are appended
    so that freshly added app support takes effect without requiring a manual reset.
    """
    existing: list[dict] = []
    if os.path.exists(RULES_PATH):
        try:
            with open(RULES_PATH) as f:
                existing = json.load(f)
        except Exception:
            pass

    # Index of app names already covered (case-insensitive, no-url rules only)
    covered = {
        r["app_name"].lower()
        for r in existing
        if r.get("app_name") and not r.get("url_contains")
    }

    new_entries = [
        rule for rule in DEFAULT_RULES
        if not rule.get("url_contains")
        and rule.get("app_name")
        and rule["app_name"].lower() not in covered
    ]

    merged = existing + new_entries
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RULES_PATH, "w") as f:
        json.dump(merged, f, indent=2)

    return merged


def check_permissions():
    try:
        import Quartz
        windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID
        )
        if not windows:
            rumps.alert(
                title="FocusLog — Permission Required",
                message=(
                    "FocusLog needs Screen Recording permission to track window titles.\n\n"
                    "Open System Settings → Privacy & Security → Screen Recording\n"
                    "and enable Terminal (or FocusLog).\n\n"
                    "Restart FocusLog after granting permission."
                )
            )
    except Exception as e:
        logger.warning(f"Permission check failed: {e}")


class FocusLogApp(rumps.App):
    def __init__(self):
        super().__init__("⏱", quit_button=None)
        os.makedirs(DATA_DIR, exist_ok=True)

        self.db = Database()
        self.db.init()

        self.classifier = Classifier(load_rules())
        self.trigger_engine = TriggerEngine()
        self._prev_session_app: str = ""

        self.watcher = WindowWatcher(
            poll_interval=5,
            on_session_end=self._on_session_end
        )

        self.menu = [
            rumps.MenuItem("Open Dashboard", callback=self.open_dashboard),
            rumps.MenuItem("Today's Summary", callback=self.show_summary),
            None,
            rumps.MenuItem("Export Today's CSV", callback=self.export_csv),
            None,
            rumps.MenuItem("Quit FocusLog", callback=self.quit_app),
        ]

        self._start_api_server()
        self.watcher.start()
        check_permissions()
        logger.info("FocusLog started")

    def _on_session_end(self, app_name, window_title, url, start_time, end_time, duration, is_idle):
        try:
            self._handle_session_end(app_name, window_title, url, start_time, end_time, duration, is_idle)
        except Exception as e:
            logger.error(f"session_end error: {e}", exc_info=True)

    def _handle_session_end(self, app_name, window_title, url, start_time, end_time, duration, is_idle):
        resolved_name = self.classifier.resolve_app_name(app_name, window_title, url)

        # Drop system-level processes — not real user activity
        if is_system_app(resolved_name):
            return

        category = self.classifier.classify(resolved_name, window_title)
        session_id = self.db.insert_session(
            app_name=resolved_name,
            window_title=window_title,
            category=category,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            is_idle=is_idle
        )

        # Trigger tagging popup for meaningful non-idle sessions
        if not is_idle and self.trigger_engine.should_trigger(
            session_id=session_id,
            app_name=resolved_name,
            duration=duration,
            prev_app_name=self._prev_session_app,
        ):
            self.trigger_engine.record_open(session_id)
            webbrowser.open_new(f"http://127.0.0.1:{PORT}/tag?session_id={session_id}")
            logger.info(f"Popup opened for session {session_id} ({resolved_name}, {duration}s)")

        self._prev_session_app = resolved_name

    def _start_api_server(self):
        api_app = create_app(self.db, watcher=self.watcher, classifier=self.classifier, tagger=self.trigger_engine)

        def _run_server():
            attempt = 0
            while True:
                attempt += 1
                try:
                    config = uvicorn.Config(
                        api_app,
                        host="127.0.0.1",
                        port=PORT,
                        log_level="warning",
                        access_log=False,
                    )
                    server = uvicorn.Server(config)
                    server.run()
                    logger.warning(f"API server exited (attempt {attempt}), restarting in 3s")
                except OSError as e:
                    if "address already in use" in str(e).lower():
                        logger.error(f"Port {PORT} in use — another FocusLog instance may be running")
                        return  # Don't retry port conflicts
                    logger.error(f"API server OSError: {e}, restarting in 3s")
                except Exception as e:
                    logger.error(f"API server error: {e}, restarting in 3s")
                import time as _t
                _t.sleep(3)

        thread = threading.Thread(target=_run_server, daemon=True)
        thread.start()

    @rumps.clicked("Open Dashboard")
    def open_dashboard(self, _):
        webbrowser.open(f"http://127.0.0.1:{PORT}")

    @rumps.clicked("Today's Summary")
    def show_summary(self, _):
        today = datetime.now().strftime("%Y-%m-%d")
        sessions = self.db.get_sessions_by_date(today)
        from tracker.analytics import compute_daily_summary
        s = compute_daily_summary(sessions)
        hours = s["total_active"] // 3600
        mins = (s["total_active"] % 3600) // 60
        dw_h = s["deep_work"] // 3600
        dw_m = (s["deep_work"] % 3600) // 60
        score = int(s["productivity_score"] * 100)
        rumps.alert(
            title=f"Today — {today}",
            message=(
                f"Active time:  {hours}h {mins}m\n"
                f"Deep work:    {dw_h}h {dw_m}m\n"
                f"Distractions: {s['distractions']}\n"
                f"Productivity: {score}%\n\n"
                f"Top app: {s['top_apps'][0]['app_name'] if s['top_apps'] else 'N/A'}"
            )
        )

    @rumps.clicked("Export Today's CSV")
    def export_csv(self, _):
        import csv
        today = datetime.now().strftime("%Y-%m-%d")
        sessions = self.db.get_sessions_by_date(today)
        path = os.path.expanduser(f"~/Desktop/focuslog-{today}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["app_name", "window_title", "category", "start_time", "end_time", "duration"]
            )
            writer.writeheader()
            writer.writerows(sessions)
        rumps.alert(f"Exported to {path}")

    def quit_app(self, _):
        self.watcher.stop()
        self.db.close()
        rumps.quit_application()


def main():
    FocusLogApp().run()


if __name__ == "__main__":
    main()
