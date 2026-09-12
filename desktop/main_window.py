"""Main application window."""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import QRect
from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from desktop.i18n import i18n, tr
from desktop.pages.applications import ApplicationsPage
from desktop.pages.dashboard import DashboardPage
from desktop.pages.jobs import JobsPage
from desktop.pages.logs import LogsPage
from desktop.pages.profile import ProfilePage
from desktop.pages.settings import SettingsPage
from desktop.services import ConfigService
from desktop.services.schedule_service import ScheduleService
from desktop.services.shutdown import get_shutdown_manager
from desktop.theme import stylesheet_for
from desktop.tray import AppTray, app_icon
from desktop.workers import PipelineWorker, start_worker
from desktop.wizard import FirstRunWizard


class MainWindow(QMainWindow):
    def __init__(self, config_service: ConfigService) -> None:
        super().__init__()
        self.config_service = config_service
        self._force_quit = False
        self._shutting_down = False
        self._worker = None
        self._thread = None
        self.setMinimumSize(900, 650)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setWindowTitle(tr("app.name"))
        self.setWindowIcon(app_icon())

        central = QWidget()
        self.setCentralWidget(central)
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setMinimumWidth(160)
        self.sidebar.setMaximumWidth(220)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(10, 14, 10, 14)
        side_layout.setSpacing(6)
        self.brand = QLabel(tr("app.name"))
        self.brand.setObjectName("Brand")
        side_layout.addWidget(self.brand)
        side_layout.addSpacing(8)

        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.dashboard = DashboardPage(config_service)
        self.jobs = JobsPage(config_service)
        self.applications = ApplicationsPage(config_service)
        self.profile = ProfilePage(config_service)
        self.settings = SettingsPage(config_service)
        self.logs = LogsPage(config_service)

        self._nav_defs = [
            ("nav.dashboard", self.dashboard),
            ("nav.jobs", self.jobs),
            ("nav.applications", self.applications),
            ("nav.profile", self.profile),
            ("nav.settings", self.settings),
            ("nav.logs", self.logs),
        ]
        self.nav_buttons: list[QPushButton] = []
        for i, (key, page) in enumerate(self._nav_defs):
            self.stack.addWidget(page)
            btn = QPushButton(tr(key))
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked=False, idx=i: self._navigate(idx))
            self.nav_buttons.append(btn)
            side_layout.addWidget(btn)
        side_layout.addStretch(1)

        shell.addWidget(self.sidebar, 0)
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.addWidget(self.stack, 1)
        shell.addWidget(content, 1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.progress_label = QLabel(tr("status.ready"))
        self.status.addPermanentWidget(self.progress_label)

        self.dashboard.search_requested.connect(self.start_search)
        self.dashboard.apply_requested.connect(self.start_apply_run)
        self.dashboard.test_requested.connect(self.run_application_test)
        self.dashboard.pause_requested.connect(self.toggle_automation_paused)
        self.dashboard.review_requested.connect(self.open_review_queue)
        self.dashboard.cancel_requested.connect(self.cancel_pipeline)
        self.dashboard.clear_jobs_requested.connect(self.clear_job_data)
        self.settings.appearance_changed.connect(self.apply_appearance_from_settings)

        self.tray = AppTray(self)
        self.tray.show()
        get_shutdown_manager().set_tray(self.tray)

        i18n.register(self.retranslate_ui)
        self._restore_geometry()
        self._navigate(0)
        self.refresh_all()

    def _restore_geometry(self) -> None:
        state = self.config_service.get_window_state()
        width = int(state.get("width") or 1180)
        height = int(state.get("height") or 760)
        width = max(900, width)
        height = max(650, height)
        self.resize(width, height)
        x = state.get("x")
        y = state.get("y")
        if isinstance(x, int) and isinstance(y, int):
            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                geo: QRect = screen.availableGeometry()
                if geo.contains(x + 40, y + 40):
                    self.move(x, y)
        if state.get("maximized"):
            self.showMaximized()

    def _save_geometry(self) -> None:
        maximized = self.isMaximized()
        # Use normal geometry when maximized so restore works
        geo = self.normalGeometry() if maximized else self.geometry()
        self.config_service.save_window_state(
            width=geo.width(),
            height=geo.height(),
            x=geo.x(),
            y=geo.y(),
            maximized=maximized,
        )

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("app.name"))
        self.brand.setText(tr("app.name"))
        for btn, (key, _) in zip(self.nav_buttons, self._nav_defs):
            btn.setText(tr(key))
        self.progress_label.setText(tr("status.ready"))
        for page in (
            self.dashboard,
            self.jobs,
            self.applications,
            self.profile,
            self.settings,
            self.logs,
        ):
            if hasattr(page, "retranslate_ui"):
                page.retranslate_ui()
        if hasattr(self.tray, "retranslate_ui"):
            self.tray.retranslate_ui()

    def apply_appearance_from_settings(self) -> None:
        cfg = self.config_service.load()
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(stylesheet_for(cfg.settings.theme or "system"))
        i18n.set_language(cfg.settings.language or "de")

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
        cfg = self.config_service.load()
        cfg.settings.dry_run = True
        self._start_pipeline(mode="review_before_submit", config_override=cfg)

    def _start_pipeline(self, mode: str, config_override=None) -> None:
        if self._thread and self._thread.isRunning():
            QMessageBox.information(self, tr("app.name"), tr("msg.pipeline_running"))
            return
        cfg = config_override or self.config_service.load()
        if bool(getattr(cfg.settings, "automation_paused", False)):
            QMessageBox.information(self, tr("app.name"), tr("msg.automation_paused"))
            return
        self.progress_label.setText(tr("status.running"))
        self.dashboard.set_status(tr("status.running"))
        self.dashboard.set_pipeline_running(True)
        worker = PipelineWorker(cfg, mode=mode)
        thread = start_worker(worker)

        def on_progress(msg: str) -> None:
            self.progress_label.setText(msg)
            self.dashboard.set_status(msg)

        def on_finished(stats: dict) -> None:
            self.dashboard.set_pipeline_running(False)
            self.progress_label.setText(tr("status.done"))
            self.dashboard.set_status(tr("status.done"))
            # Persist home coords resolved during this run (avoids re-geocoding forever).
            if stats.get("home_updated") and getattr(worker, "config", None) is not None:
                try:
                    self.config_service.save(worker.config)
                except Exception:
                    pass
            self.config_service.set_last_search(
                datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            )
            self.refresh_all()
            extra = ""
            if stats.get("source_errors"):
                extra = "\n" + "\n".join(stats.get("source_errors") or [])
            if stats.get("home_warning"):
                extra += "\n\n" + str(stats.get("home_warning"))
            if stats.get("ats_unknown") is not None:
                extra += (
                    f"\nATS: supported={stats.get('ats_supported', 0)} "
                    f"unknown={stats.get('ats_unknown', 0)} "
                    f"unsupported={stats.get('ats_detected_unsupported', 0)}"
                )
            QMessageBox.information(
                self,
                tr("msg.run_done"),
                f"{tr('msg.new')}: {stats.get('new', 0)} | {tr('msg.matches')}: {stats.get('matches', 0)} | "
                f"{tr('msg.applied')}: {stats.get('applied', 0)} | {tr('msg.review')}: {stats.get('needs_review', 0)}"
                f"{extra}",
            )

        def on_failed(err: str) -> None:
            self.dashboard.set_pipeline_running(False)
            self.progress_label.setText(tr("status.error"))
            self.dashboard.set_status(tr("status.error"))
            QMessageBox.warning(
                self,
                tr("msg.error"),
                tr("msg.error_body", err=err[:300]),
            )
            self.logs.refresh()

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.failed.connect(on_failed)
        self._worker = worker
        self._thread = thread

    def cancel_pipeline(self) -> None:
        worker = getattr(self, "_worker", None)
        if worker is not None and hasattr(worker, "request_cancel"):
            worker.request_cancel()
            self.progress_label.setText(tr("btn.cancel_search") + "…")
            self.dashboard.set_status(tr("btn.cancel_search") + "…")

    def clear_job_data(self) -> None:
        confirm = QMessageBox.question(
            self,
            tr("msg.clear_jobs_title"),
            tr("msg.clear_jobs_body"),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        cfg = self.config_service.load()
        from core.database import Database

        Database(cfg.db_path).clear_job_data(
            clear_applications=True,
            clear_source_status=True,
            clear_search_runs=True,
            clear_geocode_cache=False,
        )
        self.refresh_all()
        QMessageBox.information(self, tr("msg.clear_jobs_title"), tr("msg.clear_jobs_done"))

    def open_review_queue(self) -> None:
        self._navigate(2)
        self.applications.show_review_only()

    def toggle_automation_paused(self) -> None:
        cfg = self.config_service.load()
        self.set_automation_paused(not bool(cfg.settings.automation_paused))

    def set_automation_paused(self, paused: bool) -> None:
        cfg = self.config_service.load()
        cfg.settings.automation_paused = paused
        self.config_service.save(cfg)
        ScheduleService(cfg).sync_from_config()
        self.dashboard.refresh()
        self.settings.load_from_config()
        self.progress_label.setText(
            tr("status.paused") if paused else tr("status.resumed")
        )

    def force_quit(self) -> None:
        """Explicit exit (tray menu). Always terminates the process."""
        self._force_quit = True
        self.close()

    def _pipeline_running(self) -> bool:
        return bool(self._thread and self._thread.isRunning())

    def _confirm_exit_while_busy(self) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(tr("app.name"))
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(tr("shutdown.busy_title"))
        box.setInformativeText(tr("shutdown.busy_body"))
        cancel_btn = box.addButton(tr("shutdown.cancel"), QMessageBox.ButtonRole.RejectRole)
        quit_btn = box.addButton(tr("shutdown.quit_anyway"), QMessageBox.ButtonRole.AcceptRole)
        box.setDefaultButton(cancel_btn)
        box.exec()
        return box.clickedButton() is quit_btn

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_geometry()
        cfg = self.config_service.load()
        minimize = bool(getattr(cfg.settings, "minimize_to_tray", False))

        # Optional: hide to tray only when explicitly enabled and not forcing exit.
        if (
            not self._force_quit
            and not self._shutting_down
            and minimize
            and self.tray.isVisible()
        ):
            self.hide()
            self.tray.showMessage(
                tr("app.name"),
                tr("tray.running"),
                self.tray.MessageIcon.Information,
                2500,
            )
            event.ignore()
            return

        if self._pipeline_running() and not self._shutting_down:
            if not self._confirm_exit_while_busy():
                event.ignore()
                self._force_quit = False
                return

        self._shutting_down = True
        event.accept()
        get_shutdown_manager().shutdown(reason="window_close")

    def maybe_run_wizard(self) -> None:
        if not self.config_service.is_first_run():
            return
        wizard = FirstRunWizard(self.config_service, self)
        if wizard.exec():
            self.refresh_all()
