"""System tray integration."""

from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QSystemTrayIcon, QMenu


class AppTray(QSystemTrayIcon):
    def __init__(self, window, parent=None) -> None:
        super().__init__(parent)
        self.window = window
        self.setToolTip("Jobhuntsaver")
        # Use a simple theme icon if available
        icon = QIcon.fromTheme("applications-office")
        if icon.isNull():
            icon = window.windowIcon()
        self.setIcon(icon)

        menu = QMenu()
        open_act = QAction("Jobhuntsaver öffnen", menu)
        search_act = QAction("Jetzt suchen", menu)
        pause_act = QAction("Automation pausieren", menu)
        resume_act = QAction("Automation fortsetzen", menu)
        exit_act = QAction("Beenden", menu)
        open_act.triggered.connect(self.show_window)
        search_act.triggered.connect(window.start_search)
        pause_act.triggered.connect(lambda: window.set_automation_paused(True))
        resume_act.triggered.connect(lambda: window.set_automation_paused(False))
        exit_act.triggered.connect(window.force_quit)
        menu.addAction(open_act)
        menu.addAction(search_act)
        menu.addSeparator()
        menu.addAction(pause_act)
        menu.addAction(resume_act)
        menu.addSeparator()
        menu.addAction(exit_act)
        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def show_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()
