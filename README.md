# ⏱ FocusLog

> Local-first macOS productivity tracker. No cloud. No telemetry. Your data stays on your machine — always.

![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![No Telemetry](https://img.shields.io/badge/telemetry-none-brightgreen?style=flat-square)
![CI](https://github.com/thai-max-nguyen/focuslog/actions/workflows/ci.yml/badge.svg)

FocusLog runs silently in your macOS menu bar, logs which apps you use and for how long, then shows you a clean daily dashboard — so you have a clear, honest record of where your time actually goes.

---

## Features

| Feature | Details |
|---------|---------|
| 📊 App tracking | Every app logged with start/end timestamps |
| 💤 Idle detection | Pauses after 5 min of inactivity |
| 🏷 Categories | Work · Learning · Communication · Entertainment |
| 📅 Daily timeline | Visual bar of your day, color-coded |
| 🎯 Productivity score | Deep work ÷ total active time |
| 🏆 Top apps | Ranked leaderboard by time spent |
| 📁 CSV export | Your data, always portable |
| 🔁 Auto-start | Installs as a macOS LaunchAgent |
| 🧠 Smart task suggestions | Context-aware labels from active session, ticket IDs, and history |

## Context Inference

FocusLog infers your current task automatically across sessions using a layered rule-based system — no ML, no cloud:

| Layer | Signal | Confidence |
|-------|--------|------------|
| User tag | Explicit label from popup | 0.9 |
| Suggestion click | Label selected from suggestions | 0.8 |
| Inheritance (short gap) | Same task, gap ≤ 10 min | 0.7 |
| Inheritance (medium gap) | Same task, gap 10–30 min | 0.5 |
| Category auto-label | Communication / Entertainment apps | 0.55 |
| Unknown | No signal available | 0.3 |

Inheritance is **blocked** across Communication and Entertainment sessions — work context does not bleed through Slack or YouTube.

### Task Suggestions

When a new session starts, FocusLog suggests labels in this priority order:

1. **Active context** — the last confirmed task (expires after 2h or 30min of inactivity)
2. **Ticket ID** — extracted from the window title (e.g. `PROJ-123`)
3. **Recency cluster** — last 3 unique labels, weighted by time spent (today → 1.0, yesterday → 0.7, older → 0.4)
4. **Same-app history** — labels used in this app in the past 30 days
5. **Keyword match** — token overlap between window title and past labels
6. **Global fallback** — your most-used labels overall

### Debug Logging

Enable debug logs to see exactly why each suggestion appears:

```bash
# Run with DEBUG level to trace suggestion reasoning
FOCUSLOG_LOG_LEVEL=DEBUG focuslog
```

Example output:
```
[active_context] set=PROJ-456 ekyc conf=0.90
[suggestion] source=active_context label=PROJ-456 ekyc
[suggestion] source=ticket label=PROJ-789 (match=PROJ-789)
[suggestion] source=recency label=code review (score=3420s)
[suggestion] final=['PROJ-456 ekyc', 'PROJ-789', 'code review']
```

## Privacy

All data is stored at `~/Library/Application Support/focuslog/`. **No internet connection is ever made.** No analytics. No telemetry. See [SECURITY.md](SECURITY.md) for full details.

## Requirements

- macOS 12 Monterey or later
- Python 3.9+
- Node.js 18+ *(only needed if you want to rebuild the dashboard)*

## Install

```bash
git clone https://github.com/thai-max-nguyen/focuslog
cd focuslog
python3 setup.py
```

When prompted, grant **Screen Recording** permission:
**System Settings → Privacy & Security → Screen Recording → enable Terminal (or FocusLog)**

Then look for **⏱** in your menu bar.

## Usage

| Action | How |
|--------|-----|
| Open dashboard | Click ⏱ → Open Dashboard |
| Daily summary | Click ⏱ → Today's Summary |
| Export CSV | Click ⏱ → Export Today's CSV |
| Customize categories | Edit `~/Library/Application Support/focuslog/rules.json` |
| View API docs | `http://127.0.0.1:7331/docs` |
| Stop FocusLog | Click ⏱ → Quit FocusLog |

## Customizing Categories

Edit `~/Library/Application Support/focuslog/rules.json` (created on first run):

```json
[
  { "app_name": "VSCode", "url_contains": null, "category": "Work" },
  { "app_name": "Safari", "url_contains": "youtube.com", "category": "Entertainment" },
  { "app_name": "Safari", "url_contains": "github.com", "category": "Work" }
]
```

Restart FocusLog after changes.

## Uninstall

```bash
python3 uninstall.py
```

Removes the LaunchAgent and optionally deletes all stored data.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome.

## License

MIT — see [LICENSE](LICENSE).
