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

            CREATE TABLE IF NOT EXISTS session_tags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL UNIQUE REFERENCES sessions(id),
                task_label  TEXT NOT NULL,
                source      TEXT NOT NULL DEFAULT 'user',
                confidence  REAL NOT NULL DEFAULT 0.9,
                created_at  INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tag_skips (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL REFERENCES sessions(id),
                skipped_at  INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tags_session    ON session_tags(session_id);
            CREATE INDEX IF NOT EXISTS idx_tags_label      ON session_tags(task_label);
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

    def upsert_tag(self, session_id: int, task_label: str, source: str, confidence: float) -> int:
        import time as _time
        cur = self.conn.execute(
            """INSERT INTO session_tags (session_id, task_label, source, confidence, created_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                 task_label=excluded.task_label,
                 source=excluded.source,
                 confidence=excluded.confidence,
                 created_at=excluded.created_at""",
            (session_id, task_label, source, confidence, int(_time.time()))
        )
        self.conn.commit()
        return cur.lastrowid

    def get_tag(self, session_id: int) -> Optional[dict]:
        cur = self.conn.execute(
            "SELECT * FROM session_tags WHERE session_id = ?", (session_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_recent_tags(self, limit: int = 5) -> list:
        cur = self.conn.execute(
            """SELECT st.task_label, st.source, st.confidence, st.created_at
               FROM session_tags st
               ORDER BY st.created_at DESC, st.id DESC LIMIT ?""",
            (limit,)
        )
        return [dict(row) for row in cur.fetchall()]

    def get_tags_for_app(self, app_name: str, days: int = 30) -> list:
        import time as _time
        since = int(_time.time()) - days * 86400
        cur = self.conn.execute(
            """SELECT st.task_label, st.source, st.confidence, st.created_at,
                      COUNT(*) as frequency
               FROM session_tags st
               JOIN sessions s ON s.id = st.session_id
               WHERE s.app_name = ? AND st.created_at >= ?
               GROUP BY st.task_label
               ORDER BY (CAST(COUNT(*) AS REAL) / (1.0 + (? - MAX(st.created_at)) / 86400.0)) DESC
               LIMIT 10""",
            (app_name, since, int(_time.time()))
        )
        return [dict(row) for row in cur.fetchall()]

    def get_top_tags(self, limit: int = 10) -> list:
        cur = self.conn.execute(
            """SELECT task_label, COUNT(*) as frequency
               FROM session_tags
               GROUP BY task_label
               ORDER BY frequency DESC LIMIT ?""",
            (limit,)
        )
        return [dict(row) for row in cur.fetchall()]

    def get_all_tags(self, limit: int = 200) -> list:
        cur = self.conn.execute(
            "SELECT task_label FROM session_tags GROUP BY task_label ORDER BY MAX(created_at) DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cur.fetchall()]

    def insert_skip(self, session_id: int) -> None:
        import time as _time
        self.conn.execute(
            "INSERT INTO tag_skips (session_id, skipped_at) VALUES (?, ?)",
            (session_id, int(_time.time()))
        )
        self.conn.commit()

    def get_sessions_by_date_with_tags(self, date: str) -> list:
        """Sessions for a date, each enriched with task_label/source/confidence if tagged."""
        from datetime import datetime
        day_start = int(datetime.strptime(date, "%Y-%m-%d").timestamp())
        day_end = day_start + 86400
        cur = self.conn.execute(
            """SELECT s.*, st.task_label, st.source AS task_source, st.confidence AS task_confidence
               FROM sessions s
               LEFT JOIN session_tags st ON st.session_id = s.id
               WHERE s.start_time >= ? AND s.start_time < ? AND s.is_idle = 0
               ORDER BY s.start_time""",
            (day_start, day_end)
        )
        return [dict(row) for row in cur.fetchall()]

    def close(self):
        self.conn.close()
