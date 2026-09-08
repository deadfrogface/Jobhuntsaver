"""System tray integration."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from desktop.i18n import tr


def _fallback_app_icon() -> QIcon:
    """Simple generated icon so tray never shows without an icon on Windows."""
    pix = QPixmap(64, 64)
    pix.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#1F6FEB"))
    painter.setPen(QColor("#0B3D91"))
    painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
    painter.setPen(QColor("#FFFFFF"))
    painter.drawText(pix.rect(), int(Qt.AlignmentFlag.AlignCenter), "J")
    painter.end()
    return QIcon(pix)


class AppTray(QSystemTrayIcon):
    def __init__(self, window, parent=None) -> None:
        super().__init__(parent)
        self.window = window
        icon = QIcon.fromTheme("applications-office")
        if icon.isNull():
            icon = window.windowIcon()
        if icon.isNull():
            icon = _fallback_app_icon()
            if window.windowIcon().isNull():
                window.setWindowIcon(icon)
        self.setIcon(icon)

        menu = QMenu()
        self.open_act = QAction(menu)
        self.search_act = QAction(menu)
        self.pause_act = QAction(menu)
        self.resume_act = QAction(menu)
        self.exit_act = QAction(menu)
        self.open_act.triggered.connect(self.show_window)
        self.search_act.triggered.connect(window.start_search)
        self.pause_act.triggered.connect(lambda: window.set_automation_paused(True))
        self.resume_act.triggered.connect(lambda: window.set_automation_paused(False))
        self.exit_act.triggered.connect(window.force_quit)
        menu.addAction(self.open_act)
        menu.addAction(self.search_act)
        menu.addSeparator()
        menu.addAction(self.pause_act)
        menu.addAction(self.resume_act)
        menu.addSeparator()
        menu.addAction(self.exit_act)
        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setToolTip(tr("app.name"))
        self.open_act.setText(tr("tray.open"))
        self.search_act.setText(tr("tray.search"))
        self.pause_act.setText(tr("tray.pause"))
        self.resume_act.setText(tr("tray.resume"))
        self.exit_act.setText(tr("tray.exit"))

    def show_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()
