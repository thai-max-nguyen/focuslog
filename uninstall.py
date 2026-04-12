#!/usr/bin/env python3
"""Remove FocusLog LaunchAgent and optionally delete all data."""
import shutil
import subprocess
from pathlib import Path

PLIST = Path.home() / "Library" / "LaunchAgents" / "com.focuslog.tracker.plist"
DATA_DIR = Path.home() / "Library" / "Application Support" / "focuslog"


def main():
    print("\n🗑  FocusLog Uninstaller\n")

    if PLIST.exists():
        subprocess.run(["launchctl", "unload", str(PLIST)], check=False)
        PLIST.unlink()
        print(f"  ✓ Removed LaunchAgent")
    else:
        print("  ℹ  No LaunchAgent found")

    keep = input("\n  Keep your productivity data? [Y/n]: ").strip().lower()
    if keep in ("n", "no"):
        if DATA_DIR.exists():
            shutil.rmtree(DATA_DIR)
            print(f"  ✓ Deleted {DATA_DIR}")
    else:
        print(f"  ✓ Data kept at {DATA_DIR}")

    print("\n✅ FocusLog uninstalled.")


if __name__ == "__main__":
    main()
