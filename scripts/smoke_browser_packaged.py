"""Smoke-test optional Playwright Chromium under AppData browsers path."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from desktop.services.browser_install import (  # noqa: E402
    check_browser,
    configure_playwright_browsers_path,
    find_chromium_executable,
    preferred_browsers_dir,
    repair_browser,
)
from browser.browser_manager import BrowserManager  # noqa: E402


def main() -> int:
    """Verify browser component in AppData (or PLAYWRIGHT_BROWSERS_PATH).

    Does NOT expect Chromium next to the EXE. Pass --install to download once.
    """
    configure_playwright_browsers_path()
    target = preferred_browsers_dir()
    exe = find_chromium_executable()
    if not exe:
        if "--install" in sys.argv:
            print(f"Installing Chromium into {target} …")
            ok, msg = repair_browser()
            print(msg)
            if not ok:
                return 1
            exe = find_chromium_executable()
        else:
            print(f"SKIP: no Chromium under {target} (pass --install to download)")
            return 0

    print("FOUND", exe)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(exe.parent.parent.parent)
    configure_playwright_browsers_path()

    ok, msg = check_browser()
    print("CHECK", ok, msg.replace("\n", " | "))
    if not ok:
        return 1

    ok2, msg2 = repair_browser()
    print("REPAIR_NOOP", ok2, msg2.replace("\n", " | ")[:200])
    if not ok2:
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        mgr = BrowserManager(Path(tmp) / "profile", headless=True)
        try:
            page = mgr.get_page()
            page.goto("about:blank")
            print("LAUNCH_OK title=", repr(page.title()), "url=", page.url)
        finally:
            mgr.close()

    print("OK: AppData browser dry-run passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
