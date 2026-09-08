"""Logs viewer."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.services import ConfigService


class LogsPage(QWidget):
    def __init__(self, config_service: ConfigService, parent=None) -> None:
        super().__init__(parent)
        self.config_service = config_service
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        refresh = QPushButton("Aktualisieren")
        refresh.setObjectName("PrimaryButton")
        refresh.clicked.connect(self.refresh)
        bar = QHBoxLayout()
        bar.addWidget(refresh)
        bar.addStretch()
        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(self.view)

    def refresh(self) -> None:
        cfg = self.config_service.load()
        logs_dir = Path(cfg.settings.logs_dir)
        if not logs_dir.is_absolute():
            logs_dir = cfg.root / logs_dir
        if not logs_dir.exists():
            self.view.setPlainText("Noch keine Logs.")
            return
        files = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            files = sorted(logs_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            self.view.setPlainText("Noch keine Logs.")
            return
        latest = files[0]
        try:
            text = latest.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            text = f"Log konnte nicht gelesen werden: {exc}"
        # Show last ~2000 lines
        lines = text.splitlines()
        self.view.setPlainText("\n".join(lines[-2000:]))
