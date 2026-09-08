"""Playwright browser component helper for packaged EXE."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            path = Path(getattr(p.chromium, "executable_path", "") or "")
            return bool(path) and path.exists()
    except Exception:
        # Fallback: common Playwright cache locations on Windows
        home = Path.home()
        candidates = [
            home / "AppData" / "Local" / "ms-playwright",
            Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")),
        ]
        for base in candidates:
            if base and base.exists() and any(base.glob("chromium-*/chrome-win*/chrome.exe")):
                return True
        return False


def install_chromium() -> tuple[bool, str]:
    """Install Chromium for Playwright (user-facing button)."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            return False, detail or "Installation fehlgeschlagen."
        return True, "Browser-Komponente installiert."
    except OSError as exc:
        return False, str(exc)
