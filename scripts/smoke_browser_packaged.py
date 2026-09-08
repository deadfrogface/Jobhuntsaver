"""Smoke-test bundled Chromium next to a packaged dist folder."""

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
    repair_browser,
)
from browser.browser_manager import BrowserManager  # noqa: E402


def main() -> int:
    dist_browsers = ROOT / "dist" / "Jobhuntsaver" / "ms-playwright"
    if not dist_browsers.exists():
        print(f"SKIP: {dist_browsers} missing — run build.bat first")
        return 0

    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(dist_browsers)
    configure_playwright_browsers_path()
    exe = find_chromium_executable(dist_browsers)
    if not exe:
        print("FAIL: chrome.exe not found in dist ms-playwright")
        return 1
    print("FOUND", exe)

    ok, msg = check_browser()
    print("CHECK", ok, msg.replace("\n", " | "))
    if not ok:
        return 1

    # Ensure repair does not think it needs sys.executable when already present
    ok2, msg2 = repair_browser()
    print("REPAIR_NOOP", ok2, msg2.replace("\n", " | ")[:200])
    if not ok2:
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        mgr = BrowserManager(Path(tmp) / "profile", headless=True)
        try:
            page = mgr.get_page()
            page.goto("about:blank")
            title = page.title()
            print("LAUNCH_OK title=", repr(title), "url=", page.url)
        finally:
            mgr.close()

    print("OK: packaged Chromium dry-run passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
