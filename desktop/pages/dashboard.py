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
    cancel_requested = Signal()
    clear_jobs_requested = Signal()

    def __init__(self, config_service: ConfigService, parent=None) -> None:
        super().__init__(parent)
        self.config_service = config_service

        self.cards = {
            "this_run": StatCard("dash.this_run"),
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
        self.home_warning_label = QLabel()
        self.home_warning_label.setWordWrap(True)
        self.home_warning_label.setObjectName("WarningLabel")
        self.run_detail_label = QLabel()
        self.run_detail_label.setWordWrap(True)

        info = QVBoxLayout()
        info.addWidget(self.mode_label)
        info.addWidget(self.last_run_label)
        info.addWidget(self.next_run_label)
        info.addWidget(self.status_label)
        info.addWidget(self.home_warning_label)
        info.addWidget(self.run_detail_label)

        self.btn_search = QPushButton()
        self.btn_search.setObjectName("PrimaryButton")
        self.btn_cancel = QPushButton()
        self.btn_cancel.setObjectName("SecondaryButton")
        self.btn_cancel.setEnabled(False)
        self.btn_apply = QPushButton()
        self.btn_apply.setObjectName("SecondaryButton")
        self.btn_test = QPushButton()
        self.btn_test.setObjectName("SecondaryButton")
        self.btn_pause = QPushButton()
        self.btn_pause.setObjectName("SecondaryButton")
        self.btn_review = QPushButton()
        self.btn_review.setObjectName("SecondaryButton")
        self.btn_clear_jobs = QPushButton()
        self.btn_clear_jobs.setObjectName("SecondaryButton")
        self.btn_search.clicked.connect(self.search_requested.emit)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        self.btn_apply.clicked.connect(self.apply_requested.emit)
        self.btn_test.clicked.connect(self.test_requested.emit)
        self.btn_pause.clicked.connect(self.pause_requested.emit)
        self.btn_review.clicked.connect(self.review_requested.emit)
        self.btn_clear_jobs.clicked.connect(self.clear_jobs_requested.emit)

        actions = QHBoxLayout()
        actions.addWidget(self.btn_search)
        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.btn_apply)
        actions.addWidget(self.btn_test)
        actions.addWidget(self.btn_pause)
        actions.addWidget(self.btn_review)
        actions.addWidget(self.btn_clear_jobs)
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
        self.btn_cancel.setText(tr("btn.cancel_search"))
        self.btn_apply.setText(tr("btn.start_apply"))
        self.btn_test.setText(tr("btn.apply_test"))
        self.btn_pause.setText(tr("btn.pause_automation"))
        self.btn_review.setText(tr("btn.review_queue"))
        self.btn_clear_jobs.setText(tr("btn.clear_jobs"))
        self.status_label.setText(tr("status.ready"))
        self.refresh()

    def set_pipeline_running(self, running: bool) -> None:
        self.btn_search.setEnabled(not running)
        self.btn_cancel.setEnabled(running)
        self.btn_clear_jobs.setEnabled(not running)

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

        # Home / distance warning + last-run accounting
        loc = cfg.profile.location
        if not (loc.home_address or "").strip() and loc.home_latitude is None:
            self.home_warning_label.setText(tr("dash.home_missing"))
            self.home_warning_label.setVisible(True)
        else:
            self.home_warning_label.clear()
            self.home_warning_label.setVisible(False)

        run_id = db.latest_run_id()
        detail = ""
        if run_id:
            with db.connection() as conn:
                row = conn.execute(
                    "SELECT status, stats_json, started_at, finished_at FROM search_runs WHERE id = ?",
                    (run_id,),
                ).fetchone()
            if row:
                import json

                try:
                    st = json.loads(row["stats_json"] or "{}")
                except Exception:
                    st = {}
                if st.get("home_warning"):
                    self.home_warning_label.setText(str(st["home_warning"]))
                    self.home_warning_label.setVisible(True)
                detail = (
                    f"{tr('dash.run_stats')}: raw={st.get('raw_results', st.get('total', '—'))} | "
                    f"dup={st.get('duplicates', '—')} | dist={st.get('distance_removed', st.get('outside', '—'))} | "
                    f"neu={st.get('new_jobs', st.get('new', '—'))} | match={st.get('matches', '—')} | "
                    f"ATS unknown={st.get('ats_unknown', '—')} / supported={st.get('ats_supported', '—')}"
                )
        self.run_detail_label.setText(detail)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
