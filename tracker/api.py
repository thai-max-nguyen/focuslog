import csv
import io
import json
import time as _time
from datetime import datetime
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tracker.db import Database
from tracker.analytics import compute_daily_summary, compute_timeline_blocks
import os

_USER_TAG_CONFIDENCE = 0.9


class RuleCreate(BaseModel):
    app_name: Optional[str] = None
    url_contains: Optional[str] = None
    category: str


class TagCreate(BaseModel):
    session_id: int
    task_label: str = Field(min_length=1, max_length=200)
    source: Literal["user", "suggested"]

class TagSkip(BaseModel):
    session_id: int


def create_app(db: Database, watcher=None, classifier=None, tagger=None) -> FastAPI:
    app = FastAPI(title="FocusLog API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:7331", "http://127.0.0.1:7331"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _current_session_dict() -> Optional[dict]:
        """Read the live in-memory session from the watcher (not yet in DB)."""
        if watcher is None or not watcher.current_app or not watcher.session_start:
            return None
        if watcher.is_idle():
            return None
        now = _time.time()
        raw_app = watcher.current_app
        title = watcher.current_title
        url = watcher.current_url
        app_name = classifier.resolve_app_name(raw_app, title, url) if classifier else raw_app
        category = classifier.classify(app_name, title) if classifier else "Unknown"
        start_ts = int(watcher.session_start)
        end_ts = int(now)
        return {
            "id": -1,
            "app_name": app_name,
            "window_title": title,
            "category": category,
            "start_time": start_ts,
            "end_time": end_ts,
            "duration": end_ts - start_ts,
            "is_idle": 0,
            "is_current": True,
        }

    def _is_today(date: str) -> bool:
        return date == datetime.now().strftime("%Y-%m-%d")

    def _sessions_with_current(date: str) -> list:
        sessions = db.get_sessions_by_date(date)
        if _is_today(date):
            curr = _current_session_dict()
            if curr:
                sessions = sessions + [curr]
        return sessions

    @app.get("/api/current")
    def get_current():
        """Live in-memory session — the app being used right now."""
        return _current_session_dict()

    @app.get("/api/sessions")
    def get_sessions(date: str):
        return _sessions_with_current(date)

    @app.get("/api/summary")
    def get_summary(date: str):
        sessions = _sessions_with_current(date)
        summary = compute_daily_summary(sessions)
        db.upsert_daily_summary(
            date=date,
            total_active=summary["total_active"],
            deep_work=summary["deep_work"],
            distractions=summary["distractions"],
            productivity_score=summary["productivity_score"],
            top_apps=json.dumps(summary["top_apps"])
        )
        return summary

    @app.get("/api/timeline")
    def get_timeline(date: str):
        sessions = _sessions_with_current(date)
        return compute_timeline_blocks(sessions)

    @app.get("/api/apps")
    def get_apps(date: str):
        sessions = db.get_sessions_by_date(date)
        summary = compute_daily_summary(sessions)
        return summary["top_apps"]

    @app.get("/api/export")
    def export(date: str, fmt: str = "csv"):
        sessions = db.get_sessions_by_date(date)
        if fmt == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=["id", "app_name", "window_title", "category",
                            "start_time", "end_time", "duration"]
            )
            writer.writeheader()
            for s in sessions:
                writer.writerow({k: s.get(k, "") for k in writer.fieldnames})
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=focuslog-{date}.csv"}
            )
        raise HTTPException(status_code=400, detail="Unsupported format. Use fmt=csv")

    @app.get("/api/rules")
    def get_rules():
        return db.get_rules()

    @app.post("/api/rules")
    def create_rule(rule: RuleCreate):
        rule_id = db.insert_rule(
            app_name=rule.app_name,
            url_contains=rule.url_contains,
            category=rule.category
        )
        return {"id": rule_id, **rule.model_dump()}

    @app.delete("/api/rules/{rule_id}")
    def delete_rule(rule_id: int):
        db.delete_rule(rule_id)
        return {"deleted": rule_id}

    @app.post("/api/reclassify")
    def reclassify_unknown():
        """Reclassify all Unknown sessions using current classifier rules."""
        if classifier is None:
            raise HTTPException(status_code=503, detail="Classifier not available")
        rows = db.conn.execute(
            "SELECT id, app_name, window_title FROM sessions WHERE category='Unknown' AND is_idle=0"
        ).fetchall()
        updated = 0
        still_unknown = 0
        for row in rows:
            app_name = row["app_name"] if hasattr(row, "__getitem__") else row[1]
            window_title = row["window_title"] if hasattr(row, "__getitem__") else row[2]
            id_ = row["id"] if hasattr(row, "__getitem__") else row[0]
            cat = classifier.classify(app_name, window_title or "")
            if cat != "Unknown":
                db.conn.execute("UPDATE sessions SET category=? WHERE id=?", (cat, id_))
                updated += 1
            else:
                still_unknown += 1
        db.conn.commit()
        return {"updated": updated, "still_unknown": still_unknown}

    @app.get("/api/weekly")
    def get_weekly():
        from datetime import datetime, timedelta
        results = []
        today = datetime.now().date()  # local date, not UTC
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            date_str = d.strftime("%Y-%m-%d")
            sessions = db.get_sessions_by_date(date_str)
            summary = compute_daily_summary(sessions)
            results.append({
                "date": date_str,
                "day": d.strftime("%a"),
                **summary
            })
        return results

    @app.get("/tag")
    def tag_popup_page(session_id: int):
        """Serve the standalone tagging popup HTML."""
        popup_path = os.path.join(os.path.dirname(__file__), "tag_popup.html")
        if not os.path.exists(popup_path):
            raise HTTPException(status_code=404, detail="Popup template not found")
        with open(popup_path) as f:
            html = f.read()
        return HTMLResponse(content=html)

    @app.get("/api/tag-suggestions")
    def get_tag_suggestions(session_id: int):
        """Return context sentence + suggestions for the popup."""
        from tracker.tagger import get_suggestions, active_context
        session = db.get_session_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        # Notify active_context that the user is still active; resets the 30min idle clock.
        active_context.notify_activity()
        suggestions = get_suggestions(
            db,
            session["app_name"],
            session.get("window_title") or "",
            active_ctx=active_context.get(),
        )
        duration = session["duration"] or 0
        if duration >= 3600:
            h = duration // 3600
            m = (duration % 3600) // 60
            duration_str = f"{h}h {m}m" if m else f"{h}h"
        else:
            duration_str = f"{duration // 60} minutes"
        return {
            "session_id": session_id,
            "app_name": session["app_name"],
            "duration": duration,
            "duration_str": duration_str,
            "suggestions": suggestions,
        }

    @app.post("/api/tag")
    def create_tag(tag: TagCreate):
        """Save a tag and notify TriggerEngine to reset cooldown."""
        from tracker.tagger import active_context
        # Suggestion clicks are treated as strong signals (0.8); explicit user tags get 0.9.
        ctx_confidence = 0.8 if tag.source == "suggested" else _USER_TAG_CONFIDENCE
        db.upsert_tag(tag.session_id, tag.task_label, tag.source, ctx_confidence)
        active_context.set(tag.task_label, confidence=ctx_confidence)
        active_context.notify_activity()
        if tagger is not None:
            tagger.record_tag(tag.session_id)
        return {"ok": True}

    @app.post("/api/tag-skip")
    def tag_skip(skip: TagSkip):
        """Record that the user dismissed the popup without tagging."""
        db.insert_skip(skip.session_id)
        if tagger is not None:
            tagger.record_skip(skip.session_id)
        return {"ok": True}

    @app.get("/api/tasks")
    def get_tasks(date: str):
        """Run context inference and return task aggregates for a date."""
        from tracker.analytics import resolve_session_context, compute_context_switches, aggregate_tasks
        sessions = db.get_sessions_by_date_with_tags(date)
        if _is_today(date):
            curr = _current_session_dict()
            if curr:
                # Current session has no tag yet
                curr["task_label"] = None
                curr["task_source"] = None
                curr["task_confidence"] = None
                sessions = sessions + [curr]
        resolved = resolve_session_context(sessions)
        return {
            "tasks": aggregate_tasks(resolved),
            "total_context_switches": compute_context_switches(resolved),
        }

    # Serve pre-built React dashboard
    dist_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "dist")
    if os.path.exists(dist_path):
        app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")

    return app
