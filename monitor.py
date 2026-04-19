import os
import re
import time
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import win32gui
import win32process
import psutil

POLL_INTERVAL = 3
CHROME_HISTORY = Path(os.environ["LOCALAPPDATA"]) / "Google/Chrome/User Data/Default/History"
HISTORY_SYNC_INTERVAL = 20


@dataclass
class Event:
    timestamp: datetime
    app: str
    title: str
    url: str | None
    duration: float  # seconds


def _active_window() -> tuple[str, str]:
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        app = psutil.Process(pid).name().replace(".exe", "").lower()
    except Exception:
        app = "unknown"
    return app, title


def _chrome_title(window_title: str) -> str | None:
    m = re.match(r"^(.+?)\s+-\s+(?:Google Chrome|Chromium)$", window_title)
    return m.group(1).strip() if m else None


class Monitor:
    def __init__(self):
        self._title_to_url: dict[str, str] = {}
        self._last_history_sync = 0.0
        self._last_app = ""
        self._last_title = ""
        self._since = datetime.now()

    def _sync_history(self):
        if time.time() - self._last_history_sync < HISTORY_SYNC_INTERVAL:
            return
        if not CHROME_HISTORY.exists():
            return
        try:
            tmp = tempfile.mktemp(suffix=".db")
            shutil.copy2(CHROME_HISTORY, tmp)
            conn = sqlite3.connect(tmp)
            rows = conn.execute(
                "SELECT title, url FROM urls ORDER BY last_visit_time DESC LIMIT 1000"
            ).fetchall()
            conn.close()
            os.unlink(tmp)
            self._title_to_url = {r[0].strip(): r[1] for r in rows if r[0]}
        except Exception:
            pass
        self._last_history_sync = time.time()

    def _resolve_url(self, app: str, title: str) -> str | None:
        if app not in ("chrome", "chromium"):
            return None
        page_title = _chrome_title(title)
        if not page_title:
            return None
        return self._title_to_url.get(page_title)

    def poll(self) -> Event | None:
        self._sync_history()
        app, title = _active_window()
        if app == self._last_app and title == self._last_title:
            return None
        now = datetime.now()
        duration = (now - self._since).total_seconds()
        if self._last_app:
            event = Event(
                timestamp=self._since,
                app=self._last_app,
                title=self._last_title,
                url=self._resolve_url(self._last_app, self._last_title),
                duration=duration,
            )
            self._last_app = app
            self._last_title = title
            self._since = now
            return event
        self._last_app = app
        self._last_title = title
        self._since = now
        return None

    def run(self, callback):
        while True:
            e = self.poll()
            if e:
                callback(e)
            time.sleep(POLL_INTERVAL)
