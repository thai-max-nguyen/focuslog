from collections import defaultdict
from typing import Any

DEEP_WORK_THRESHOLD = 25 * 60   # 25 minutes
DISTRACTION_THRESHOLD = 60       # switches under 60 seconds


def compute_daily_summary(sessions: list[dict]) -> dict[str, Any]:
    if not sessions:
        return {
            "total_active": 0,
            "deep_work": 0,
            "distractions": 0,
            "productivity_score": 0.0,
            "top_apps": [],
            "categories": {},
        }

    total_active = sum(s["duration"] for s in sessions)
    deep_work = sum(s["duration"] for s in sessions if s["duration"] >= DEEP_WORK_THRESHOLD)

    distractions = 0
    for i in range(len(sessions) - 1):
        curr = sessions[i]
        nxt = sessions[i + 1]
        if curr["app_name"] != nxt["app_name"] and curr["duration"] < DISTRACTION_THRESHOLD:
            distractions += 1

    productivity_score = deep_work / total_active if total_active > 0 else 0.0

    app_time: dict[str, int] = defaultdict(int)
    for s in sessions:
        app_time[s["app_name"]] += s["duration"]
    top_apps = sorted(
        [{"app_name": k, "duration": v} for k, v in app_time.items()],
        key=lambda x: x["duration"],
        reverse=True
    )[:10]

    categories: dict[str, int] = defaultdict(int)
    for s in sessions:
        categories[s["category"]] += s["duration"]

    return {
        "total_active": total_active,
        "deep_work": deep_work,
        "distractions": distractions,
        "productivity_score": round(productivity_score, 4),
        "top_apps": top_apps,
        "categories": dict(categories),
    }


def compute_timeline_blocks(sessions: list[dict]) -> list[dict]:
    """Merge consecutive sessions of same app within 30s gap."""
    if not sessions:
        return []

    merged = []
    current = dict(sessions[0])

    for s in sessions[1:]:
        gap = s["start_time"] - current["end_time"]
        if s["app_name"] == current["app_name"] and gap <= 30:
            current["end_time"] = s["end_time"]
            current["duration"] += s["duration"] + gap
        else:
            merged.append(current)
            current = dict(s)

    merged.append(current)
    return merged
