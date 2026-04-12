import csv
import io
import json
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tracker.db import Database
from tracker.analytics import compute_daily_summary, compute_timeline_blocks
import os


class RuleCreate(BaseModel):
    app_name: Optional[str] = None
    url_contains: Optional[str] = None
    category: str


def create_app(db: Database) -> FastAPI:
    app = FastAPI(title="FocusLog API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:7331", "http://127.0.0.1:7331"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/sessions")
    def get_sessions(date: str):
        return db.get_sessions_by_date(date)

    @app.get("/api/summary")
    def get_summary(date: str):
        sessions = db.get_sessions_by_date(date)
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
        sessions = db.get_sessions_by_date(date)
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

    # Serve pre-built React dashboard
    dist_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "dist")
    if os.path.exists(dist_path):
        app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")

    return app
