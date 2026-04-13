import ctypes
import time
import threading
from typing import Callable, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Load system frameworks once at import time
_CF = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
_AX = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")

_CF.CFStringCreateWithCString.restype = ctypes.c_void_p
_CF.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
_CF.CFArrayGetCount.restype = ctypes.c_long
_CF.CFArrayGetCount.argtypes = [ctypes.c_void_p]
_CF.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
_CF.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
_CF.CFStringGetCString.restype = ctypes.c_bool
_CF.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
_CF.CFRelease.restype = None
_CF.CFRelease.argtypes = [ctypes.c_void_p]

_AX.AXUIElementCreateApplication.restype = ctypes.c_void_p
_AX.AXUIElementCreateApplication.argtypes = [ctypes.c_int32]
_AX.AXUIElementCopyAttributeValue.restype = ctypes.c_int32
_AX.AXUIElementCopyAttributeValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]

_kCFStringEncodingUTF8 = 0x08000100
_AX_WINDOWS        = _CF.CFStringCreateWithCString(None, b"AXWindows",       _kCFStringEncodingUTF8)
_AX_TITLE          = _CF.CFStringCreateWithCString(None, b"AXTitle",         _kCFStringEncodingUTF8)
_AX_FOCUSED_WINDOW = _CF.CFStringCreateWithCString(None, b"AXFocusedWindow", _kCFStringEncodingUTF8)
_AX_DOCUMENT       = _CF.CFStringCreateWithCString(None, b"AXDocument",      _kCFStringEncodingUTF8)


def _cf_to_str(cfstr: int) -> str:
    if not cfstr:
        return ""
    buf = ctypes.create_string_buffer(4096)
    ok = _CF.CFStringGetCString(cfstr, buf, 4096, _kCFStringEncodingUTF8)
    return buf.value.decode("utf-8", errors="replace") if ok else ""


def _ax_get_window_info(pid: int) -> Tuple[str, str]:
    """Return (window_title, document_url) for the frontmost window.

    document_url is populated for browsers that expose AXDocument (Chrome, Arc,
    Safari, Firefox).  Falls back to empty string if unavailable.
    """
    app_ref = _AX.AXUIElementCreateApplication(pid)
    if not app_ref:
        return "", ""

    title = ""
    url = ""

    try:
        # 1. Try focused window (fastest path)
        win_out = ctypes.c_void_p()
        err = _AX.AXUIElementCopyAttributeValue(app_ref, _AX_FOCUSED_WINDOW, ctypes.byref(win_out))
        window = win_out.value if err == 0 and win_out.value else None

        wins_ref = None  # track for release
        if not window:
            # 2. Fall back to iterating AXWindows list
            wins_out = ctypes.c_void_p()
            err = _AX.AXUIElementCopyAttributeValue(app_ref, _AX_WINDOWS, ctypes.byref(wins_out))
            if err == 0 and wins_out.value:
                wins_ref = wins_out.value
                count = _CF.CFArrayGetCount(wins_ref)
                for i in range(min(count, 5)):
                    w = _CF.CFArrayGetValueAtIndex(wins_ref, i)
                    t_out = ctypes.c_void_p()
                    if _AX.AXUIElementCopyAttributeValue(w, _AX_TITLE, ctypes.byref(t_out)) == 0 and t_out.value:
                        t = _cf_to_str(t_out.value)
                        _CF.CFRelease(t_out.value)
                        if t:
                            window = w
                            title = t
                            break

        if window:
            # Get title if not already extracted above
            if not title:
                t_out = ctypes.c_void_p()
                if _AX.AXUIElementCopyAttributeValue(window, _AX_TITLE, ctypes.byref(t_out)) == 0 and t_out.value:
                    title = _cf_to_str(t_out.value)
                    _CF.CFRelease(t_out.value)

            # Try AXDocument — gives us the actual URL for browser windows
            doc_out = ctypes.c_void_p()
            if _AX.AXUIElementCopyAttributeValue(window, _AX_DOCUMENT, ctypes.byref(doc_out)) == 0 and doc_out.value:
                raw = _cf_to_str(doc_out.value)
                _CF.CFRelease(doc_out.value)
                if raw.startswith(("http://", "https://")):
                    url = raw

        if wins_ref:
            _CF.CFRelease(wins_ref)

    finally:
        _CF.CFRelease(app_ref)

    return title, url


def get_active_window_info() -> Tuple[str, str, str]:
    """Returns (app_name, window_title, url) for the frontmost window."""
    try:
        from AppKit import NSWorkspace
        workspace = NSWorkspace.sharedWorkspace()
        active_app = workspace.frontmostApplication()
        if not active_app:
            return "Unknown", "", ""
        app_name = str(active_app.localizedName() or "")
        pid = active_app.processIdentifier()
        title, url = _ax_get_window_info(pid)
        return app_name, title, url
    except Exception as e:
        logger.error(f"Error getting active window: {e}")
        return "Unknown", "", ""


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
        self.current_url: str = ""
        self.session_start: float = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def is_idle(self) -> bool:
        return get_idle_seconds() >= IDLE_THRESHOLD

    def _poll_once(self) -> Tuple[str, str, str]:
        app, title, url = get_active_window_info()
        now = time.time()

        if self.is_idle():
            if self.current_app and self.session_start:
                try:
                    self._flush_session(now, is_idle=True)
                except Exception as e:
                    logger.error(f"Flush error (idle): {e}")
            # Always reset state — even if flush failed
            self.current_app = ""
            self.current_title = ""
            self.current_url = ""
            self.session_start = 0.0
            return app, title, url

        if app != self.current_app:
            if self.current_app and self.session_start:
                try:
                    self._flush_session(now)
                except Exception as e:
                    logger.error(f"Flush error (switch): {e}")
            # Always update state — even if flush failed, so we don't get stuck
            self.current_app = app
            self.current_title = title
            self.current_url = url
            self.session_start = now
        else:
            # Only update title/url if non-empty — AX can transiently return ""
            if title:
                self.current_title = title
            if url:
                self.current_url = url

        return app, title, url

    def _flush_session(self, end_time: float, is_idle: bool = False):
        if not self.current_app or not self.session_start:
            return

        # When idle is detected the user stopped IDLE_THRESHOLD seconds ago — trim back
        actual_end = (end_time - IDLE_THRESHOLD) if is_idle else end_time
        actual_end = max(actual_end, self.session_start)

        start_ts = int(self.session_start)
        end_ts = int(actual_end)
        duration = end_ts - start_ts
        if duration < 2:
            return

        if self.on_session_end:
            self.on_session_end(
                app_name=self.current_app,
                window_title=self.current_title,
                url=self.current_url,
                start_time=start_ts,
                end_time=end_ts,
                duration=duration,
                is_idle=is_idle,
            )

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        now = time.time()
        if self.current_app and self.session_start:
            try:
                self._flush_session(now)
            except Exception as e:
                logger.error(f"Flush error (stop): {e}")

    def _loop(self):
        while self._running:
            t0 = time.time()
            try:
                self._poll_once()
            except Exception as e:
                logger.error(f"Watcher loop error: {e}")
            elapsed = time.time() - t0
            time.sleep(max(0.0, self.poll_interval - elapsed))
