from collections import defaultdict
from typing import Any

DEEP_WORK_THRESHOLD = 25 * 60   # 25 minutes
DISTRACTION_THRESHOLD = 60       # switches under 60 seconds
GAP_FILL_MIN = 10                # fill gaps >= 10 seconds with Idle block


def compute_daily_summary(sessions: list[dict]) -> dict[str, Any]:
    if not sessions:
        return {
            "total_active": 0,
            "deep_work": 0,
            "distractions": 0,
            "productivity_score": 0.0,
            "top_apps": [],
            "categories": {},
            "longest_session": 0,
            "longest_session_app": "",
            "peak_hour": -1,
            "switch_rate": 0.0,
            "focus_efficiency": 0.0,
            "worst_distraction_app": "",
        }

    total_active = sum(s["duration"] for s in sessions)
    deep_work = sum(s["duration"] for s in sessions if s["duration"] >= DEEP_WORK_THRESHOLD)

    # Distractions: context switches where the outgoing session was brief
    distractions = 0
    distraction_targets: dict[str, int] = defaultdict(int)
    for i in range(len(sessions) - 1):
        curr = sessions[i]
        nxt = sessions[i + 1]
        if curr["app_name"] != nxt["app_name"] and curr["duration"] < DISTRACTION_THRESHOLD:
            distractions += 1
            distraction_targets[nxt["app_name"]] += 1

    productivity_score = deep_work / total_active if total_active > 0 else 0.0

    # Longest single session
    longest = max(sessions, key=lambda s: s["duration"])
    longest_session = longest["duration"]
    longest_session_app = longest["app_name"]

    # Peak hour: hour of day with most active seconds
    hour_totals: dict[int, int] = defaultdict(int)
    for s in sessions:
        hour = (s["start_time"] % 86400) // 3600
        hour_totals[hour] += s["duration"]
    peak_hour = max(hour_totals, key=lambda h: hour_totals[h]) if hour_totals else -1

    # Context switch rate per hour
    span_hours = (sessions[-1]["end_time"] - sessions[0]["start_time"]) / 3600
    switch_rate = round(distractions / span_hours, 1) if span_hours > 0 else 0.0

    # Focus efficiency: Work time / total active time (excludes comm/entertainment/unknown)
    work_secs = sum(s["duration"] for s in sessions if s["category"] == "Work")
    focus_efficiency = round(work_secs / total_active, 4) if total_active > 0 else 0.0

    # Worst distraction app (most jumped-to after a short session)
    worst_distraction_app = (
        max(distraction_targets, key=lambda k: distraction_targets[k])
        if distraction_targets else ""
    )

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
        "longest_session": longest_session,
        "longest_session_app": longest_session_app,
        "peak_hour": peak_hour,
        "switch_rate": switch_rate,
        "focus_efficiency": focus_efficiency,
        "worst_distraction_app": worst_distraction_app,
    }


def compute_timeline_blocks(sessions: list[dict]) -> list[dict]:
    """Merge consecutive same-app sessions within 30s gap; fill larger gaps with Idle blocks."""
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
            # Fill meaningful gaps with an Idle placeholder so the timeline has no holes
            if gap >= GAP_FILL_MIN:
                merged.append({
                    "id": -1,
                    "app_name": "Idle",
                    "window_title": "",
                    "category": "Idle",
                    "start_time": current["end_time"],
                    "end_time": s["start_time"],
                    "duration": gap,
                    "is_idle": 1,
                })
            current = dict(s)

    merged.append(current)
    return merged


_CATEGORY_AUTO_LABELS: frozenset = frozenset({"Communication", "Entertainment"})
_INHERITANCE_HIGH_GAP = 10 * 60   # ≤10 min → confidence 0.7
_INHERITANCE_LOW_GAP  = 30 * 60   # ≤30 min → confidence 0.5


def resolve_session_context(sessions: list) -> list:
    """
    Resolve context (task_label, source, confidence) for each session.

    Each session dict must have keys: id, category, start_time, end_time,
    duration, task_label (str|None), task_source (str|None).
    Returns new dicts with additional keys: context_label, context_source,
    context_confidence.

    Inheritance decay:
      gap ≤ 10 min  → confidence 0.7
      gap 10–30 min → confidence 0.5
      gap > 30 min  → break chain
    """
    resolved = []
    prev_label = None
    prev_end_time = None

    for session in sessions:
        tagged_label = session.get("task_label")

        # --- User/suggested tag (highest confidence) ---
        if tagged_label:
            ctx = {
                **session,
                "context_label": tagged_label,
                "context_source": session.get("task_source") or "user",
                "context_confidence": 0.9,
            }
            prev_label = tagged_label
            prev_end_time = session["end_time"]
            resolved.append(ctx)
            continue

        # --- Category auto-label (Communication / Entertainment) ---
        if session.get("category") in _CATEGORY_AUTO_LABELS:
            ctx = {
                **session,
                "context_label": session["category"],
                "context_source": "inferred_category",
                "context_confidence": 0.55,
            }
            # Break the inheritance chain — work context must not bleed across
            # a distraction or messaging session.
            prev_label = None
            prev_end_time = session["end_time"]
            resolved.append(ctx)
            continue

        # --- Inheritance with decay ---
        idle_gap = (
            (session["start_time"] - prev_end_time)
            if prev_end_time is not None
            else _INHERITANCE_LOW_GAP + 1
        )

        if prev_label and session.get("category") not in _CATEGORY_AUTO_LABELS:
            if idle_gap <= _INHERITANCE_HIGH_GAP:
                confidence: float | None = 0.7
            elif idle_gap <= _INHERITANCE_LOW_GAP:
                confidence = 0.5
            else:
                confidence = None   # gap too large → break chain
        else:
            confidence = None

        if confidence is not None:
            ctx = {
                **session,
                "context_label": prev_label,
                "context_source": "inferred",
                "context_confidence": confidence,
            }
            prev_end_time = session["end_time"]
            resolved.append(ctx)
            continue

        # --- UNKNOWN (break condition met, no tag, no category fallback) ---
        ctx = {
            **session,
            "context_label": "UNKNOWN",
            "context_source": "unknown",
            "context_confidence": 0.3,
        }
        prev_label = None   # break the inheritance chain
        prev_end_time = session["end_time"]
        resolved.append(ctx)

    return resolved


def compute_context_switches(resolved_sessions: list) -> int:
    """
    Count the number of real context switches.
    A switch requires both sessions to have confidence >= 0.6 and different labels.
    UNKNOWN sessions are skipped — they are data gaps, not switches.
    """
    switches = 0
    prev = None
    for session in resolved_sessions:
        label = session.get("context_label")
        conf = session.get("context_confidence", 0.0)
        if label == "UNKNOWN" or conf < 0.6:
            continue
        if prev and prev["context_label"] != label:
            switches += 1
        prev = session
    return switches


def aggregate_tasks(resolved_sessions: list) -> list:
    """
    Group resolved sessions by context_label and sum durations.
    'Uncategorized' (UNKNOWN sessions) is always last.
    """
    buckets: dict = {}

    for session in resolved_sessions:
        raw_label = session.get("context_label", "UNKNOWN")
        label = "Uncategorized" if raw_label == "UNKNOWN" else raw_label
        src = session.get("context_source", "unknown")

        if label not in buckets:
            buckets[label] = {"total_duration": 0, "session_count": 0, "sources": {}}
        buckets[label]["total_duration"] += session.get("duration", 0)
        buckets[label]["session_count"] += 1
        buckets[label]["sources"][src] = buckets[label]["sources"].get(src, 0) + 1

    # Sort by total_duration descending; Uncategorized always last
    non_uncategorized = sorted(
        [{"task_label": k, **v} for k, v in buckets.items() if k != "Uncategorized"],
        key=lambda x: -x["total_duration"],
    )
    result = non_uncategorized
    if "Uncategorized" in buckets:
        result = result + [{"task_label": "Uncategorized", **buckets["Uncategorized"]}]
    return result
