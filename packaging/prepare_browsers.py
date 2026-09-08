"""Download Playwright Chromium into packaging/ms-playwright for bundling."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = Path(__file__).resolve().parent / "ms-playwright"


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(TARGET)
    print(f"Installing Chromium into {TARGET} …")
    proc = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        env=env,
    )
    if proc.returncode != 0:
        print("playwright install failed", file=sys.stderr)
        return proc.returncode
    chrome = sorted(TARGET.glob("chromium-*/chrome-win*/chrome.exe"))
    if not chrome:
        print("Chromium executable not found after install", file=sys.stderr)
        return 1
    print(f"OK: {chrome[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
