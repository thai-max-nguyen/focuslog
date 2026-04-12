import time
import threading
from typing import Callable, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def get_active_window_info() -> Tuple[str, str]:
    """Returns (app_name, window_title) for the frontmost window."""
    try:
        from AppKit import NSWorkspace
        import Quartz

        workspace = NSWorkspace.sharedWorkspace()
        active_app = workspace.frontmostApplication()
        app_name = str(active_app.localizedName() or "")
        pid = active_app.processIdentifier()

        windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        if windows:
            for win in windows:
                if win.get("kCGWindowOwnerPID") == pid:
                    title = str(win.get("kCGWindowName") or "")
                    if title:
                        return app_name, title
        return app_name, ""
    except Exception as e:
        logger.error(f"Error getting active window: {e}")
        return "Unknown", ""


def get_idle_seconds() -> float:
    """Returns seconds since last keyboard/mouse input."""
    try:
        import Quartz
        return Quartz.CGEventSourceSecondsSinceLastEventType(
            Quartz.kCGEventSourceStateHIDSystemState,
            Quartz.kCGAnyInputEventType
        )
    except Exception:
        return 0.0


IDLE_THRESHOLD = 300  # 5 minutes


class WindowWatcher:
    def __init__(self, poll_interval: int = 5, on_session_end: Optional[Callable] = None):
        self.poll_interval = poll_interval
        self.on_session_end = on_session_end
        self.current_app: str = ""
        self.current_title: str = ""
        self.session_start: float = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def is_idle(self) -> bool:
        return get_idle_seconds() >= IDLE_THRESHOLD

    def _poll_once(self) -> Tuple[str, str]:
        app, title = get_active_window_info()
        now = time.time()

        if self.is_idle():
            if self.current_app and self.session_start:
                self._flush_session(now, is_idle=True)
            self.current_app = ""
            self.current_title = ""
            self.session_start = 0.0
            return app, title

        if app != self.current_app:
            if self.current_app and self.session_start:
                self._flush_session(now)
            self.current_app = app
            self.current_title = title
            self.session_start = now
        else:
            self.current_title = title

        return app, title

    def _flush_session(self, end_time: float, is_idle: bool = False):
        if not self.current_app or not self.session_start:
            return
        duration = int(end_time - self.session_start)
        if duration < 2:
            return
        if self.on_session_end:
            self.on_session_end(
                app_name=self.current_app,
                window_title=self.current_title,
                start_time=int(self.session_start),
                end_time=int(end_time),
                duration=duration,
                is_idle=is_idle
            )

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        now = time.time()
        if self.current_app and self.session_start:
            self._flush_session(now)

    def _loop(self):
        while self._running:
            try:
                self._poll_once()
            except Exception as e:
                logger.error(f"Watcher loop error: {e}")
            time.sleep(self.poll_interval)
