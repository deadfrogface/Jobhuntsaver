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
from desktop.i18n import tr
from desktop.services import ConfigService


class StatCard(QFrame):
    def __init__(self, title_key: str, parent=None) -> None:
        super().__init__(parent)
        self._title_key = title_key
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        self.value = QLabel("0")
        self.value.setObjectName("CardValue")
        self.caption = QLabel()
        self.caption.setObjectName("CardTitle")
        layout.addWidget(self.value)
        layout.addWidget(self.caption)
        self.retranslate()

    def retranslate(self) -> None:
        self.caption.setText(tr(self._title_key))

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
            "jobs_found_today": StatCard("dash.found_today"),
            "new_today": StatCard("dash.new"),
            "matches_ge_75": StatCard("dash.matches"),
            "applications_today": StatCard("dash.applied"),
            "needs_review": StatCard("dash.needs_review"),
            "captcha": StatCard("dash.captcha"),
            "errors": StatCard("dash.errors"),
        }

        grid = QGridLayout()
        for i, card in enumerate(self.cards.values()):
            grid.addWidget(card, i // 4, i % 4)

        self.mode_label = QLabel()
        self.last_run_label = QLabel()
        self.next_run_label = QLabel()
        self.status_label = QLabel()

        info = QVBoxLayout()
        info.addWidget(self.mode_label)
        info.addWidget(self.last_run_label)
        info.addWidget(self.next_run_label)
        info.addWidget(self.status_label)

        self.btn_search = QPushButton()
        self.btn_search.setObjectName("PrimaryButton")
        self.btn_apply = QPushButton()
        self.btn_apply.setObjectName("SecondaryButton")
        self.btn_test = QPushButton()
        self.btn_test.setObjectName("SecondaryButton")
        self.btn_pause = QPushButton()
        self.btn_pause.setObjectName("SecondaryButton")
        self.btn_review = QPushButton()
        self.btn_review.setObjectName("SecondaryButton")
        self.btn_search.clicked.connect(self.search_requested.emit)
        self.btn_apply.clicked.connect(self.apply_requested.emit)
        self.btn_test.clicked.connect(self.test_requested.emit)
        self.btn_pause.clicked.connect(self.pause_requested.emit)
        self.btn_review.clicked.connect(self.review_requested.emit)

        actions = QHBoxLayout()
        actions.addWidget(self.btn_search)
        actions.addWidget(self.btn_apply)
        actions.addWidget(self.btn_test)
        actions.addWidget(self.btn_pause)
        actions.addWidget(self.btn_review)
        actions.addStretch()

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addSpacing(12)
        layout.addLayout(info)
        layout.addSpacing(8)
        layout.addLayout(actions)
        layout.addStretch()

        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        for card in self.cards.values():
            card.retranslate()
        self.btn_search.setText(tr("btn.search_now"))
        self.btn_apply.setText(tr("btn.start_apply"))
        self.btn_test.setText(tr("btn.apply_test"))
        self.btn_pause.setText(tr("btn.pause_automation"))
        self.btn_review.setText(tr("btn.review_queue"))
        self.status_label.setText(tr("status.ready"))
        self.refresh()

    def refresh(self) -> None:
        cfg = self.config_service.load()
        db = Database(cfg.db_path)
        stats = db.dashboard_stats()
        for key, card in self.cards.items():
            card.set_value(stats.get(key, 0))
        mode = cfg.settings.mode
        dry = tr("dash.on") if cfg.settings.dry_run else tr("dash.off")
        paused = tr("dash.paused") if cfg.settings.automation_paused else tr("dash.active")
        auto = tr("dash.on") if cfg.settings.run_automatically else tr("dash.off")
        self.mode_label.setText(
            f"{tr('dash.mode')}: {mode}  |  {tr('dash.dry_run')}: {dry}  |  "
            f"{tr('dash.automation')}: {auto} ({paused})"
        )
        meta = self.config_service.load_meta()
        self.last_run_label.setText(
            f"{tr('dash.last_search')}: {meta.get('last_search_run') or '—'}"
        )
        self.next_run_label.setText(
            f"{tr('dash.next_run')}: {meta.get('next_scheduled_run') or '—'}"
        )

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
