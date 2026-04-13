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

### New table: `tag_skips`

```sql
CREATE TABLE IF NOT EXISTS tag_skips (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    skipped_at  INTEGER NOT NULL
);
```

Used for future trigger/suggestion tuning. Never shown in the dashboard UI.

---

## 4. Tagging Popup

### 4.1 Trigger Logic

Show popup on session end when **both** conditions are true:
- Session has no existing tag
- Duration meets threshold (either condition):
  - `duration >= 7 minutes` — always trigger
  - `duration >= 3 minutes AND previous session was same app` — user is focused, short sessions still matter

The 3-minute relaxed threshold catches meaningful short bursts (e.g., a quick Jira ticket check before a Figma review) that the 7-minute rule would silently skip.

Trigger timing:
- **On session end only** (app switch or idle). Sessions are written to the DB when they end, so the session_id is available at trigger time. Mid-session triggering is deferred to Phase 2.

**Do NOT trigger when:**
- Duration < 3 minutes
- Session is already tagged
- A popup is already open (deduplicate by session_id)
- Last popup was shown < 20 minutes ago (cooldown — see §4.1a)
- FocusLog has been running < 60 seconds (startup grace period)

### 4.1a Cooldown Logic

Minimum 20 minutes between any two tagging prompts, regardless of how many sessions end in that window. This prevents notification fatigue — if the user is switching apps rapidly, they should not be interrupted repeatedly.

Cooldown escalation on skip:
- Base cooldown: 20 min
- After 1 skip: 30 min
- After 2 consecutive skips: 45 min
- After 3+ consecutive skips: 60 min
- Cooldown resets when user successfully tags a session

Cooldown state is tracked in memory only (resets on FocusLog restart). It is not persisted — the goal is session-level comfort, not long-term suppression.

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
| Click × or Skip | Record skip (POST /api/tag-skip), close window |
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

For a given `(app_name, window_title)`, evaluate sources in priority order and merge results:

**Source 1 — Recent tags (last 3–5 sessions) [HIGHEST PRIORITY]**
Query the 5 most recent tagged sessions regardless of app. Return their task_labels as-is.
*Why:* Users frequently work on the same task across multiple consecutive sessions (e.g., reviewing Jira, switching to Figma, back to Jira — all "NFC review"). Recency is the single strongest signal for what the user is still doing right now.

**Source 2 — Past tags for same app**
Query last 30 days of tags where `session.app_name = current_app_name`. Score by `frequency × recency_weight` where `recency_weight = 1 / (days_ago + 1)`. Take top 3.

**Source 3 — Window title keyword match**
Strip common stop words from `window_title`. Match remaining tokens against all past `task_label` strings. If overlap >= 1 token, include that label.

**Source 4 — Global top tags (fallback)**
User's top 2 most-used labels across all time. Only used when fewer than 2 suggestions found from sources 1–3.

**Merge & deduplicate** → keep top 4, preserving priority order. Source 1 results always appear first if present.

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

### 5.5 Skip Tracking

`POST /api/tag-skip`

Called when user dismisses the popup without tagging (× button, Skip link, or Escape key).

Body:
```json
{
  "session_id": 42
}
```

Response: `{"ok": true}`

Saved to a `tag_skips` table (session_id, skipped_at). No tag row is created. This data enables future tuning of: (1) trigger timing — if most skips happen on short sessions, raise the threshold; (2) suggestion quality — if users always type custom labels instead of using suggestions, the suggestion engine needs work. Skip data is never shown to the user.

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
            # Break detected — assign UNKNOWN but do NOT count as a context switch.
            # Rationale: the user may simply have gone idle and resumed the same task.
            # Counting every break as a switch would inflate the metric and make it
            # untrustworthy. UNKNOWN is a gap in data, not evidence of a switch.
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
| `tracker/db.py` | Add `session_tags` + `tag_skips` tables; `upsert_tag()`, `get_tag()`, `get_tags_for_app()`, `insert_skip()` |
| `tracker/api.py` | Add `/tag` (GET page), `/api/tag-suggestions`, `/api/tag` (POST), `/api/tag-skip` (POST), `/api/tasks` |
| `tracker/analytics.py` | Add `compute_context_timeline()`, enrich `compute_daily_summary()` with tasks + switches |
| `tracker/main.py` | Wire popup trigger to `on_session_end` with cooldown + relaxed threshold logic |
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
