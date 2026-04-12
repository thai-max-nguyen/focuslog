# Changelog

All notable changes to FocusLog are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.0] — 2026-04-12

### Added
- App usage tracking via macOS AppKit and Quartz APIs
- Idle detection (5-minute threshold)
- Activity classification with configurable rules (`rules.json`)
- Daily timeline bar with category color coding
- Category pie chart and productivity score
- Top-apps leaderboard
- CSV export from dashboard and menu bar
- Menu bar icon (⏱) with quick daily summary popup
- LaunchAgent auto-start on login
- `setup.py` one-command installer
- `uninstall.py` clean removal tool
- FastAPI REST API at `http://127.0.0.1:7331` (auto-docs at `/docs`)
