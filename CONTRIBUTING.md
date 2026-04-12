# Contributing to FocusLog

Thanks for your interest! FocusLog is intentionally small and focused.

## Development Setup

```bash
git clone https://github.com/thai-max-nguyen/focuslog
cd focuslog
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Guidelines

- **Local-first, always.** No network calls, no telemetry, no cloud.
- **Lightweight.** CPU usage must stay under 1% at idle.
- **Tests required.** All new Python code needs tests in `tests/`.
- **macOS first.** Windows support is a stretch goal.
- **Commit style:** `feat:`, `fix:`, `chore:`, `docs:`

## Pull Requests

1. Fork → branch (`feat/your-feature`) → PR
2. Write tests first (TDD)
3. Describe the *why* in your PR description
