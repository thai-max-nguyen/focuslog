# Task Tagging & Context Switching — Phase 1 Design

**Date:** 2026-04-13
**Status:** Approved
**Scope:** FocusLog — Phase 1 MVP

---

## 1. Overview

This feature adds **task-level awareness** to FocusLog. Today the app tracks *which apps* you used. After this feature, it tracks *what you were actually working on*.

Two additions:
1. **Task Tagging** — a floating popup that captures user intent after a meaningful session
2. **Context Switching** — an inference engine that determines when the user actually changed what they were working on (not just which app)

Phase 1 surfaces: **Sessions table (A)** + **Daily Overview tasks block (B)**.

---

## 2. Core Concepts

### Task Label
A short human-readable string the user assigns to a session. Examples: "NFC review", "Bug fix eKYC", "Writing Jira ticket". No predefined taxonomy — freeform with suggestions.

### Context
`context = task_label assigned to a session`. A context switch only occurs when the task label changes, not when the app changes. Switching from Jira → Figma while both are tagged "NFC review" = same context.

### Confidence
Every session has a context confidence score:
- `0.9` — user-tagged (`source = "user"` or `"suggested"`)
- `0.6` — inferred from previous session (`source = "inferred"`)
- `0.3` — cannot determine (`source = "unknown"`)

---

## 3. Data Model

### New table: `session_tags`

```sql
CREATE TABLE IF NOT EXISTS session_tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    task_label  TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'user',   -- user | suggested | inferred | unknown
    confidence  REAL NOT NULL DEFAULT 0.9,
    created_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tags_session ON session_tags(session_id);
CREATE INDEX IF NOT EXISTS idx_tags_label   ON session_tags(task_label);
```

One tag per session. If user re-tags a session, the existing row is updated (upsert on session_id).

---

## 4. Tagging Popup

### 4.1 Trigger Logic

Show popup when **both** conditions are true:
- Session duration >= 7 minutes (skip micro-sessions)
- Session has no existing tag

Trigger timing:
- **On session end only** (app switch or idle). Sessions are written to the DB when they end, so the session_id is available at trigger time. Mid-session triggering is deferred to Phase 2 (requires tracking in-progress sessions before DB insertion).

**Do NOT trigger when:**
- Session duration < 7 min
- Session is already tagged
- A popup is already open (deduplicate by session_id)
- User has skipped > 3 consecutive popups in the last hour (back-off: skip next 3 sessions)
- FocusLog has been running < 60 seconds (startup grace period)

### 4.2 Popup Delivery

The daemon calls `webbrowser.open_new('http://127.0.0.1:7331/tag?session_id=X')`.

The `/tag` route serves a **standalone HTML page** (not the React SPA). On load, JavaScript:
1. Calls `window.resizeTo(380, 300)` to constrain window size
2. Calls `window.moveTo(screen.width - 400, screen.height - 340)` to position bottom-right
3. Auto-focuses the first suggestion button

This works in all browsers without native dependencies.

### 4.3 Popup Structure (Context-first, approved)

```
┌─────────────────────────────────────┐
│ ⏱ FocusLog                        × │  ← thin header bar
├─────────────────────────────────────┤
│ You spent 12 minutes on Jira        │  ← context (human sentence)
│                                     │
│ What were you working on?           │  ← prompt (subtle)
│                                     │
│ [✏ Writing ticket] [🐛 Bug fix]    │  ← suggestion pills (2–4)
│ [🔍 NFC review]                    │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Or type your own…               │ │  ← optional input
│ └─────────────────────────────────┘ │
│                          [Skip]     │  ← right-aligned, subtle
└─────────────────────────────────────┘
```

**UX order is fixed:** Context → Prompt → Suggestions → Input → Skip. Do not reorder.

### 4.4 Interaction Behavior

| Action | Result |
|--------|--------|
| Click suggestion pill | POST tag (source=suggested), close window |
| Type + Enter | POST tag (source=user), close window |
| Click × or Skip | Record skip, close window (no tag saved) |
| Press Escape | Same as Skip |

Auto-close after successful save — no confirmation screen.

### 4.5 Context Sentence Generation

Format: `"You spent {duration} on {app_name}"`

Duration formatting:
- < 60s → not triggered (below threshold)
- 1–59 min → "X minutes"
- ≥ 60 min → "X hour Y minutes" (or "X hours" if exact)

App name: use the resolved `app_name` from the session (already human-readable: "Jira", "Figma", not "arc").

---

## 5. Suggestion Engine

### 5.1 Algorithm (no ML, keyword matching only)

For a given `(app_name, window_title)`:

**Source 1 — Past tags for same app** (recency-weighted)
Query last 30 days of tags where `session.app_name = current_app_name`. Sort by frequency × recency. Take top 3.

**Source 2 — Window title keyword match**
Strip common stop words from `window_title`. Match remaining tokens against all past `task_label` strings. If overlap >= 1 token, include that label.

**Merge & deduplicate** → keep top 4. If fewer than 2 suggestions found, pad with the user's 2 most-used labels globally.

### 5.2 API Endpoint

`GET /api/tag-suggestions?session_id=X`

Response:
```json
{
  "session_id": 42,
  "app_name": "Jira",
  "duration": 720,
  "suggestions": ["Writing ticket", "Bug fix eKYC", "NFC review"]
}
```

### 5.3 Tasks Endpoint

`GET /api/tasks?date=YYYY-MM-DD`

Runs the context inference engine over all sessions for the date and returns task aggregates.

Response:
```json
{
  "tasks": [
    {"task_label": "NFC review", "total_duration": 6120, "session_count": 4, "sources": {"user": 2, "inferred": 2}},
    {"task_label": "Bug fix eKYC", "total_duration": 2880, "session_count": 2, "sources": {"user": 1, "inferred": 1}},
    {"task_label": "UNKNOWN", "total_duration": 720, "session_count": 3, "sources": {"unknown": 3}}
  ],
  "total_context_switches": 4
}
```

### 5.4 Tag Submission

`POST /api/tag`

Body:
```json
{
  "session_id": 42,
  "task_label": "NFC review",
  "source": "suggested"
}
```

Response: `{"ok": true}`

On success → popup calls `window.close()`.

---

## 6. Context Inference Engine

Run at query time when computing analytics (not stored, derived on demand).

### 6.1 Per-session Resolution

```
for each session in chronological order:
    if session has tag:
        context = tag.task_label
        confidence = 0.9
        source = "user" | "suggested"
    else:
        check break conditions vs previous session:
            - idle gap > 10 minutes
            - category changed drastically (Work → Entertainment/Unknown)
        if no break:
            context = previous.context
            confidence = 0.6
            source = "inferred"
        else:
            context = "UNKNOWN"
            confidence = 0.3
            source = "unknown"
```

### 6.2 Context Switch Detection

A switch is counted when:
- `current.context != previous.context`
- AND `current.confidence >= 0.6`
- AND `previous.confidence >= 0.6`
- UNKNOWN contexts are excluded from switch counting

### 6.3 Output Fields (added to analytics)

```python
{
  "total_context_switches": int,
  "context_timeline": [
    {
      "session_id": int,
      "task_label": str,       # or "UNKNOWN"
      "source": str,           # user | suggested | inferred | unknown
      "confidence": float,
      "duration": int
    }
  ],
  "tasks": [
    {
      "task_label": str,
      "total_duration": int,   # seconds
      "session_count": int,
      "sources": {"user": N, "inferred": N}
    }
  ]
}
```

---

## 7. Dashboard Changes

### 7.1 Sessions Page — Task Column (A)

Add a `Task` column to the existing sessions table.

| Display state | Appearance |
|--------------|------------|
| User-tagged | Colored pill (task label text, full opacity) |
| Inferred | Muted pill with italic text + "~" prefix |
| Untagged | "＋ Tag" button — opens popup for that session |

Clicking "＋ Tag" opens `http://127.0.0.1:7331/tag?session_id=X` (same popup, retroactive tagging).

### 7.2 Daily Overview — Today's Tasks Block (B)

New section below the existing stats grid. Title: **"Today's Tasks"**.

Layout: vertical bar chart — one row per task_label, sorted by total duration descending.

```
Today's Tasks
─────────────────────────────────────
🎯 NFC review          ████████████  1h 42m
🐛 Bug fix eKYC        ████          48m
📝 Writing ticket      ██            18m
❓ Unknown             ▒             12m   ← grey, bottom
─────────────────────────────────────
Context switches today: 4
```

- Unknown is always last, always grey
- Inferred time shown with same color as user-tagged (no visual distinction — it's transparent to the user)
- "Context switches today: N" — single line below the chart, clickable → scrolls to Sessions table

---

## 8. New Files & Changed Files

### New files
| File | Purpose |
|------|---------|
| `tracker/tagger.py` | Suggestion engine + popup trigger logic |
| `tracker/tag_popup.html` | Standalone popup HTML (served by FastAPI at `/tag`) |

### Changed files
| File | Changes |
|------|---------|
| `tracker/db.py` | Add `session_tags` table, `upsert_tag()`, `get_tag()`, `get_tags_for_app()` |
| `tracker/api.py` | Add `/tag` (GET page), `/api/tag-suggestions`, `/api/tag` (POST), `/api/tasks` |
| `tracker/analytics.py` | Add `compute_context_timeline()`, enrich `compute_daily_summary()` with tasks + switches |
| `tracker/main.py` | Wire popup trigger to `on_session_end` and mid-session 5-min check |
| `dashboard/src/pages/Sessions.tsx` | Add Task column, inline tag button |
| `dashboard/src/pages/DailyOverview.tsx` | Add Today's Tasks section |
| `dashboard/src/App.tsx` | Add `SessionTag`, `TaskSummary` types |

---

## 9. Out of Scope (Phase 1)

| Feature | Reason deferred |
|---------|----------------|
| `project` field | Adds hierarchy complexity before tagging habit is established |
| Timeline switch markers (C) | Needs clean tagging data first; noisy in Phase 1 |
| Weekly task trends (D) | Needs 2+ weeks of history |
| Tag editing from Overview | Sessions page handles this; avoid duplicate surfaces |
| AI-powered suggestions | Simple keyword matching sufficient for Phase 1 |

---

## 10. Phase 1 Product Philosophy

This feature succeeds if users tag 3+ sessions per day within the first week — not because they're forced to, but because the popup is fast enough that it doesn't feel like work. Accuracy matters more than completeness: a day with 5 confident tags is more valuable than 20 inferred ones. Build the habit loop first; enrich the analytics once the data exists.
