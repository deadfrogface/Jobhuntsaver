"""Desktop application bootstrap."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# High-DPI before QApplication
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

# Packaged Chromium path before any Playwright import
try:
    from desktop.services.browser_install import configure_playwright_browsers_path

    configure_playwright_browsers_path()
except Exception:
    pass

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from desktop.i18n import i18n
from desktop.main_window import MainWindow
from desktop.services import ConfigService
from desktop.theme import stylesheet_for


def apply_appearance(app: QApplication, config_service: ConfigService) -> None:
    cfg = config_service.load()
    lang = (cfg.settings.language or "de").lower()
    if lang not in {"de", "en"}:
        lang = "de"
    i18n.set_language(lang)
    theme_pref = cfg.settings.theme or "system"
    app.setStyleSheet(stylesheet_for(theme_pref))


def run() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Jobhuntsaver")
    app.setOrganizationName("Jobhuntsaver")
    app.setQuitOnLastWindowClosed(False)

    config_service = ConfigService()
    apply_appearance(app, config_service)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.warning(
            None,
            "Jobhuntsaver",
            "System tray is not available. The app can still be used.",
        )

    window = MainWindow(config_service)
    window.show()
    window.maybe_run_wizard()
    return app.exec()


def main() -> int:
    if "--smoke-browser" in sys.argv:
        return _smoke_browser()
    return run()


def _smoke_browser() -> int:
    """Headless packaged check: detect Chromium and open about:blank."""
    import tempfile

    from desktop.services.browser_install import check_browser, configure_playwright_browsers_path
    from browser.browser_manager import BrowserManager

    log_path = Path(sys.executable).resolve().parent / "smoke_browser_result.txt"
    lines: list[str] = []
    try:
        configure_playwright_browsers_path()
        ok, msg = check_browser()
        lines.append(msg)
        if not ok:
            log_path.write_text("\n".join(lines), encoding="utf-8")
            return 1
        with tempfile.TemporaryDirectory() as tmp:
            mgr = BrowserManager(Path(tmp) / "profile", headless=True)
            try:
                page = mgr.get_page()
                page.goto("about:blank")
                lines.append(f"SMOKE_BROWSER_OK {page.url}")
            finally:
                mgr.close()
        log_path.write_text("\n".join(lines), encoding="utf-8")
        return 0
    except Exception as exc:  # noqa: BLE001
        lines.append(f"FAIL: {exc}")
        try:
            log_path.write_text("\n".join(lines), encoding="utf-8")
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
