#!/usr/bin/env python3
"""
FocusLog setup script.
Run: python3 setup.py
"""
VERSION = "0.2.0"
import os
import shutil
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path.home() / "Library" / "Application Support" / "focuslog"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_DEST = LAUNCH_AGENTS_DIR / "com.focuslog.tracker.plist"
FOCUSLOG_DIR = Path(__file__).parent.resolve()


def run(cmd, cwd=None):
    print(f"  → {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, check=True, cwd=cwd)


def main():
    print("\n🚀 FocusLog Setup\n")
    print("This will:")
    print("  1. Install Python dependencies")
    print("  2. Build the React dashboard")
    print("  3. Install a LaunchAgent (auto-start on login)")
    print()
    input("Press Enter to continue (Ctrl+C to cancel)...\n")

    print("── Installing Python dependencies")
    run([sys.executable, "-m", "pip", "install", "-r", str(FOCUSLOG_DIR / "requirements.txt")])

    print("\n── Building React dashboard")
    dash = FOCUSLOG_DIR / "dashboard"
    if not (dash / "node_modules").exists():
        if shutil.which("npm"):
            run(["npm", "install"], cwd=dash)
        else:
            print("  ⚠  npm not found — skipping dashboard build (pre-built dist/ will be used)")
    if shutil.which("npm"):
        run(["npm", "run", "build"], cwd=dash)

    print("\n── Creating data directory")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  → {DATA_DIR}")

    print("\n── Installing LaunchAgent")
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    template_path = FOCUSLOG_DIR / "launchagent" / "com.focuslog.tracker.plist.template"
    plist = (
        template_path.read_text()
        .replace("PYTHON_PATH", sys.executable)
        .replace("FOCUSLOG_DIR", str(FOCUSLOG_DIR))
        .replace("FOCUSLOG_DATA", str(DATA_DIR))
    )
    PLIST_DEST.write_text(plist)
    run(["launchctl", "load", str(PLIST_DEST)])

    print("\n✅ FocusLog is running!")
    print(f"   Dashboard → http://127.0.0.1:7331")
    print(f"   Data      → {DATA_DIR}")
    print(f"   Rules     → {DATA_DIR / 'rules.json'}")
    print("\n   Look for ⏱ in your menu bar.")


if __name__ == "__main__":
    main()
