"""Desktop application bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path when running as module or script
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from desktop.main_window import MainWindow
from desktop.services import ConfigService
from desktop.styles import APP_STYLESHEET


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Jobhuntsaver")
    app.setOrganizationName("Jobhuntsaver")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(APP_STYLESHEET)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            "Jobhuntsaver",
            "System-Tray ist nicht verfügbar. Die App kann trotzdem geöffnet werden.",
        )

    config_service = ConfigService()
    window = MainWindow(config_service)
    window.show()
    window.maybe_run_wizard()
    return app.exec()


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
