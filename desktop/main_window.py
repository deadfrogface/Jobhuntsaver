"""Main application window."""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from desktop.pages.applications import ApplicationsPage
from desktop.pages.dashboard import DashboardPage
from desktop.pages.jobs import JobsPage
from desktop.pages.logs import LogsPage
from desktop.pages.profile import ProfilePage
from desktop.pages.settings import SettingsPage
from desktop.services import ConfigService
from desktop.services.schedule_service import ScheduleService
from desktop.tray import AppTray
from desktop.workers import PipelineWorker, start_worker
from desktop.wizard import FirstRunWizard


class MainWindow(QMainWindow):
    def __init__(self, config_service: ConfigService) -> None:
        super().__init__()
        self.config_service = config_service
        self._force_quit = False
        self._worker = None
        self._thread = None
        self.setWindowTitle("Jobhuntsaver")
        self.resize(1180, 760)

        central = QWidget()
        self.setCentralWidget(central)
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        side_layout = QVBoxLayout(sidebar)
        brand = QLabel("Jobhuntsaver")
        brand.setObjectName("Brand")
        side_layout.addWidget(brand)
        side_layout.addSpacing(12)

        self.stack = QStackedWidget()
        self.dashboard = DashboardPage(config_service)
        self.jobs = JobsPage(config_service)
        self.applications = ApplicationsPage(config_service)
        self.profile = ProfilePage(config_service)
        self.settings = SettingsPage(config_service)
        self.logs = LogsPage(config_service)
        pages = [
            ("Dashboard", self.dashboard),
            ("Jobs", self.jobs),
            ("Bewerbungen", self.applications),
            ("Profil", self.profile),
            ("Einstellungen", self.settings),
            ("Logs", self.logs),
        ]
        self.nav_buttons: list[QPushButton] = []
        for i, (label, page) in enumerate(pages):
            self.stack.addWidget(page)
            btn = QPushButton(label)
            btn.setProperty("class", "NavButton")
            btn.setProperty("active", "false")
            btn.setStyleSheet("")  # class via stylesheet selector
            btn.setObjectName("Nav")
            btn.setProperty("className", "NavButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked=False, idx=i: self._navigate(idx))
            # Use dynamic property for stylesheet
            btn.setProperty("active", "false")
            btn.setStyleSheet(
                "QPushButton { text-align:left; padding:10px 14px; border:none; "
                "border-radius:6px; color:#d7e4ec; background:transparent; }"
                "QPushButton:checked { background:rgba(61,139,120,0.35); color:white; font-weight:600; }"
                "QPushButton:hover { background:rgba(255,255,255,0.08); }"
            )
            self.nav_buttons.append(btn)
            side_layout.addWidget(btn)
        side_layout.addStretch()

        shell.addWidget(sidebar)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.addWidget(self.stack)
        shell.addWidget(content, 1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.progress_label = QLabel("Bereit")
        self.status.addPermanentWidget(self.progress_label)

        self.dashboard.search_requested.connect(self.start_search)
        self.dashboard.apply_requested.connect(self.start_apply_run)
        self.dashboard.test_requested.connect(self.run_application_test)
        self.dashboard.pause_requested.connect(lambda: self.set_automation_paused(True))
        self.dashboard.review_requested.connect(self.open_review_queue)

        self.tray = AppTray(self)
        self.tray.show()

        self._navigate(0)
        self.refresh_all()

    def _navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        page = self.stack.widget(index)
        if hasattr(page, "refresh"):
            page.refresh()
        if hasattr(page, "load_from_config"):
            page.load_from_config()

    def refresh_all(self) -> None:
        self.dashboard.refresh()
        self.jobs.refresh()
        self.applications.refresh()
        self.profile.load_from_config()
        self.settings.load_from_config()
        self.logs.refresh()

    def start_search(self) -> None:
        self._start_pipeline(mode="search_only")

    def start_apply_run(self) -> None:
        cfg = self.config_service.load()
        mode = cfg.settings.mode
        if mode == "search_only":
            mode = "review_before_submit"
        self._start_pipeline(mode=mode)

    def run_application_test(self) -> None:
        """Test workflow: force dry_run and review mode."""
        cfg = self.config_service.load()
        cfg.settings.dry_run = True
        self._start_pipeline(mode="review_before_submit", config_override=cfg)

    def _start_pipeline(self, mode: str, config_override=None) -> None:
        if self._thread and self._thread.isRunning():
            QMessageBox.information(self, "Jobhuntsaver", "Es läuft bereits ein Auftrag.")
            return
        cfg = config_override or self.config_service.load()
        self.progress_label.setText("Läuft…")
        self.dashboard.set_status("Läuft…")
        worker = PipelineWorker(cfg, mode=mode)
        thread = start_worker(worker)

        def on_progress(msg: str) -> None:
            self.progress_label.setText(msg)
            self.dashboard.set_status(msg)

        def on_finished(stats: dict) -> None:
            self.progress_label.setText("Fertig")
            self.dashboard.set_status("Fertig")
            self.config_service.set_last_search(
                datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            )
            self.refresh_all()
            QMessageBox.information(
                self,
                "Lauf abgeschlossen",
                f"Neu: {stats.get('new', 0)} | Matches: {stats.get('matches', 0)} | "
                f"Beworben: {stats.get('applied', 0)} | Review: {stats.get('needs_review', 0)}",
            )

        def on_failed(err: str) -> None:
            self.progress_label.setText("Fehler")
            self.dashboard.set_status("Fehler")
            QMessageBox.warning(
                self,
                "Fehler",
                "Ein Schritt ist fehlgeschlagen. Details stehen in den Logs.\n\n"
                f"{err[:300]}",
            )
            self.logs.refresh()

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.failed.connect(on_failed)
        self._worker = worker
        self._thread = thread

    def open_review_queue(self) -> None:
        self._navigate(2)
        self.applications.show_review_only()

    def set_automation_paused(self, paused: bool) -> None:
        cfg = self.config_service.load()
        cfg.settings.automation_paused = paused
        self.config_service.save(cfg)
        ScheduleService(cfg).sync_from_config()
        self.dashboard.refresh()
        self.settings.load_from_config()
        self.progress_label.setText("Automation pausiert" if paused else "Automation fortgesetzt")

    def force_quit(self) -> None:
        self._force_quit = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._force_quit or not self.tray.isVisible():
            event.accept()
            return
        self.hide()
        self.tray.showMessage(
            "Jobhuntsaver",
            "Läuft weiter im Infobereich.",
            self.tray.MessageIcon.Information,
            2500,
        )
        event.ignore()

    def maybe_run_wizard(self) -> None:
        if not self.config_service.is_first_run():
            return
        wizard = FirstRunWizard(self.config_service, self)
        if wizard.exec():
            self.refresh_all()
