"""Playwright browser manager with persistent profile.

Uses bundled Chromium when present (packaged EXE). Never requires
``python -m playwright`` from a frozen executable.
"""

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path
from typing import Any

logger = logging.getLogger("jobhuntsaver")


def _find_system_chrome() -> str | None:
    candidates = []
    if platform.system() == "Windows":
        for base in [
            os.environ.get("PROGRAMFILES", r"C:\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            os.path.expandvars(r"%LOCALAPPDATA%"),
        ]:
            candidates.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
    elif platform.system() == "Darwin":
        candidates.append("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    else:
        candidates.extend(["/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium"])
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _resolve_chromium_executable() -> str | None:
    """Prefer bundled / PLAYWRIGHT_BROWSERS_PATH Chromium over system Chrome."""
    try:
        from desktop.services.browser_install import (
            configure_playwright_browsers_path,
            find_chromium_executable,
        )

        configure_playwright_browsers_path()
        bundled = find_chromium_executable()
        if bundled and bundled.exists():
            return str(bundled)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Bundled Chromium lookup failed: %s", exc)
    return None


class BrowserManager:
    def __init__(self, profile_dir: Path, headless: bool = True) -> None:
        self.headless = headless
        self.profile_dir = Path(profile_dir)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright: Any = None
        self._context: Any = None
        self._page: Any = None
        try:
            from desktop.services.browser_install import configure_playwright_browsers_path

            configure_playwright_browsers_path()
        except Exception:
            pass

    def get_page(self):
        if self._page and not self._page.is_closed():
            return self._page
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright fehlt. Entwicklung: pip install playwright && python -m playwright install chromium"
            ) from exc

        if self._playwright is None:
            self._playwright = sync_playwright().start()

        launch_kwargs = dict(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            viewport={"width": 1280, "height": 800},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            ignore_default_args=["--enable-automation"],
        )

        chromium = _resolve_chromium_executable()
        if chromium:
            launch_kwargs["executable_path"] = chromium
        else:
            # Last resort: system Chrome (dev machines)
            chrome = _find_system_chrome()
            if chrome:
                launch_kwargs["executable_path"] = chrome
                logger.warning("Using system Chrome; bundled Playwright Chromium not found")

        try:
            self._context = self._playwright.chromium.launch_persistent_context(**launch_kwargs)
        except Exception as exc:
            if "executable doesn't exist" in str(exc).lower():
                raise RuntimeError(
                    "Playwright Chromium fehlt. In der App: Einstellungen → Browser → "
                    "„Browser-Komponente reparieren“. "
                    "Entwicklung: python -m playwright install chromium"
                ) from exc
            # Fallback non-headless if headless fails
            if self.headless:
                logger.warning("Headless launch failed (%s); retrying visible browser", exc)
                self.headless = False
                launch_kwargs["headless"] = False
                self._context = self._playwright.chromium.launch_persistent_context(**launch_kwargs)
            else:
                raise
        self._page = self._context.new_page()
        return self._page

    def close(self) -> None:
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
            self._page = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
