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
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
