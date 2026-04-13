import sqlite3
import os
from typing import Optional


DATA_DIR = os.path.expanduser("~/Library/Application Support/focuslog")


class Database:
    def __init__(self, path: Optional[str] = None):
        if path is None:
            os.makedirs(DATA_DIR, exist_ok=True)
            path = os.path.join(DATA_DIR, "focuslog.db")
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # WAL mode: readers don't block writers and vice versa —
        # prevents "database is locked" when the watcher and API write concurrently.
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")

    def init(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name     TEXT NOT NULL,
                window_title TEXT,
                category     TEXT DEFAULT 'Unknown',
                start_time   INTEGER NOT NULL,
                end_time     INTEGER,
                duration     INTEGER,
                is_idle      BOOLEAN DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS daily_summary (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                date               TEXT NOT NULL UNIQUE,
                total_active       INTEGER DEFAULT 0,
                deep_work          INTEGER DEFAULT 0,
                distractions       INTEGER DEFAULT 0,
                productivity_score REAL DEFAULT 0.0,
                top_apps           TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS rules (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name     TEXT,
                url_contains TEXT,
                category     TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_start ON sessions(start_time);
        """)
        self.conn.commit()

    def get_tables(self) -> list:
        cur = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        return [row[0] for row in cur.fetchall()]

    def insert_session(
        self,
        app_name: str,
        window_title: str,
        category: str,
        start_time: int,
        end_time: int,
        duration: int,
        is_idle: bool
    ) -> int:
        cur = self.conn.execute(
            """INSERT INTO sessions
               (app_name, window_title, category, start_time, end_time, duration, is_idle)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (app_name, window_title, category, start_time, end_time, duration, int(is_idle))
        )
        self.conn.commit()
        return cur.lastrowid

    def get_sessions_by_date(self, date: str) -> list:
        from datetime import datetime
        # Use local midnight so day boundaries match the user's clock, not UTC
        day_start = int(datetime.strptime(date, "%Y-%m-%d").timestamp())
        day_end = day_start + 86400
        cur = self.conn.execute(
            "SELECT * FROM sessions WHERE start_time >= ? AND start_time < ? AND is_idle = 0 ORDER BY start_time",
            (day_start, day_end)
        )
        return [dict(row) for row in cur.fetchall()]

    def insert_rule(self, app_name: Optional[str], url_contains: Optional[str], category: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO rules (app_name, url_contains, category) VALUES (?, ?, ?)",
            (app_name, url_contains, category)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_rules(self) -> list:
        cur = self.conn.execute("SELECT * FROM rules")
        return [dict(row) for row in cur.fetchall()]

    def delete_rule(self, rule_id: int):
        self.conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        self.conn.commit()

    def upsert_daily_summary(self, date: str, total_active: int, deep_work: int,
                              distractions: int, productivity_score: float, top_apps: str):
        self.conn.execute(
            """INSERT INTO daily_summary
               (date, total_active, deep_work, distractions, productivity_score, top_apps)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(date) DO UPDATE SET
                 total_active=excluded.total_active,
                 deep_work=excluded.deep_work,
                 distractions=excluded.distractions,
                 productivity_score=excluded.productivity_score,
                 top_apps=excluded.top_apps""",
            (date, total_active, deep_work, distractions, productivity_score, top_apps)
        )
        self.conn.commit()

    def get_daily_summary(self, date: str) -> Optional[dict]:
        cur = self.conn.execute("SELECT * FROM daily_summary WHERE date = ?", (date,))
        row = cur.fetchone()
        return dict(row) if row else None

    def close(self):
        self.conn.close()
