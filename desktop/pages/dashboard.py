"""Dashboard page."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.database import Database
from desktop.services import ConfigService


class StatCard(QFrame):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        self.value = QLabel("0")
        self.value.setObjectName("CardValue")
        caption = QLabel(title)
        caption.setObjectName("CardTitle")
        layout.addWidget(self.value)
        layout.addWidget(caption)

    def set_value(self, text: str | int) -> None:
        self.value.setText(str(text))


class DashboardPage(QWidget):
    search_requested = Signal()
    apply_requested = Signal()
    test_requested = Signal()
    pause_requested = Signal()
    review_requested = Signal()

    def __init__(self, config_service: ConfigService, parent=None) -> None:
        super().__init__(parent)
        self.config_service = config_service

        self.cards = {
            "jobs_found_today": StatCard("Heute gefunden"),
            "new_today": StatCard("Neu"),
            "matches_ge_75": StatCard("Matches ≥75%"),
            "applications_today": StatCard("Beworben"),
            "needs_review": StatCard("Needs Review"),
            "captcha": StatCard("CAPTCHA"),
            "errors": StatCard("Fehler"),
        }

        grid = QGridLayout()
        for i, card in enumerate(self.cards.values()):
            grid.addWidget(card, i // 4, i % 4)

        self.mode_label = QLabel()
        self.last_run_label = QLabel()
        self.next_run_label = QLabel()
        self.status_label = QLabel("Bereit")

        info = QVBoxLayout()
        info.addWidget(self.mode_label)
        info.addWidget(self.last_run_label)
        info.addWidget(self.next_run_label)
        info.addWidget(self.status_label)

        btn_search = QPushButton("Jetzt suchen")
        btn_search.setObjectName("PrimaryButton")
        btn_apply = QPushButton("Bewerbungslauf starten")
        btn_apply.setObjectName("SecondaryButton")
        btn_test = QPushButton("Bewerbungstest")
        btn_test.setObjectName("SecondaryButton")
        btn_pause = QPushButton("Automation pausieren")
        btn_pause.setObjectName("SecondaryButton")
        btn_review = QPushButton("Review-Warteschlange")
        btn_review.setObjectName("SecondaryButton")
        btn_search.clicked.connect(self.search_requested.emit)
        btn_apply.clicked.connect(self.apply_requested.emit)
        btn_test.clicked.connect(self.test_requested.emit)
        btn_pause.clicked.connect(self.pause_requested.emit)
        btn_review.clicked.connect(self.review_requested.emit)

        actions = QHBoxLayout()
        actions.addWidget(btn_search)
        actions.addWidget(btn_apply)
        actions.addWidget(btn_test)
        actions.addWidget(btn_pause)
        actions.addWidget(btn_review)
        actions.addStretch()

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addSpacing(12)
        layout.addLayout(info)
        layout.addSpacing(8)
        layout.addLayout(actions)
        layout.addStretch()

    def refresh(self) -> None:
        cfg = self.config_service.load()
        db = Database(cfg.db_path)
        stats = db.dashboard_stats()
        for key, card in self.cards.items():
            card.set_value(stats.get(key, 0))
        mode = cfg.settings.mode
        dry = "an" if cfg.settings.dry_run else "aus"
        paused = "pausiert" if cfg.settings.automation_paused else "aktiv"
        auto = "an" if cfg.settings.run_automatically else "aus"
        self.mode_label.setText(f"Modus: {mode}  |  Dry Run: {dry}  |  Automation: {auto} ({paused})")
        meta = self.config_service.load_meta()
        self.last_run_label.setText(f"Letzte Suche: {meta.get('last_search_run') or '—'}")
        self.next_run_label.setText(f"Nächster geplanter Lauf: {meta.get('next_scheduled_run') or '—'}")

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
