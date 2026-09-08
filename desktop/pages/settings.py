"""Settings page – modes, sources, automation, browser."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.database import Database
from desktop.services import ConfigService
from desktop.services.browser_install import playwright_available
from desktop.services.schedule_service import ScheduleService
from desktop.workers import BrowserInstallWorker, start_worker


SOURCES = [
    ("bundesagentur", "Bundesagentur"),
    ("indeed", "Indeed"),
    ("linkedin", "LinkedIn"),
    ("stepstone", "StepStone"),
    ("xing", "XING"),
    ("company_sites", "Unternehmensseiten"),
]


class SettingsPage(QWidget):
    def __init__(self, config_service: ConfigService, parent=None) -> None:
        super().__init__(parent)
        self.config_service = config_service
        self._install_thread = None
        self._install_worker = None

        layout = QVBoxLayout(self)

        # Modes
        mode_box = QGroupBox("Bewerbungsmodus")
        mode_layout = QVBoxLayout(mode_box)
        self.mode_group = QButtonGroup(self)
        self.mode_search = QRadioButton("Nur Suche – nie bewerben")
        self.mode_review = QRadioButton("Vor Absenden prüfen")
        self.mode_auto = QRadioButton("Vollautomatisch (sichere Bewerbungen)")
        for i, btn in enumerate((self.mode_search, self.mode_review, self.mode_auto)):
            self.mode_group.addButton(btn, i)
            mode_layout.addWidget(btn)
        self.dry_run = QCheckBox("Dry Run (nie endgültig absenden)")
        mode_layout.addWidget(self.dry_run)
        layout.addWidget(mode_box)

        # Sources
        src_box = QGroupBox("Jobquellen")
        src_layout = QVBoxLayout(src_box)
        self.source_checks: dict[str, QCheckBox] = {}
        self.source_status = QLabel()
        for key, label in SOURCES:
            cb = QCheckBox(label)
            self.source_checks[key] = cb
            src_layout.addWidget(cb)
        src_layout.addWidget(self.source_status)
        layout.addWidget(src_box)

        # Search settings
        search_box = QGroupBox("Suche")
        sform = QFormLayout(search_box)
        self.published_days = QSpinBox()
        self.published_days.setRange(1, 90)
        self.min_match_dash = QSpinBox()
        self.min_match_dash.setRange(0, 100)
        self.max_distance = QSpinBox()
        self.max_distance.setRange(1, 300)
        sform.addRow("Veröffentlichungsalter (Tage)", self.published_days)
        sform.addRow("Min. Match Anzeige", self.min_match_dash)
        sform.addRow("Max. Distanz (km)", self.max_distance)
        layout.addWidget(search_box)

        # Auto apply
        apply_box = QGroupBox("Auto-Apply")
        aform = QFormLayout(apply_box)
        self.min_match_apply = QSpinBox()
        self.min_match_apply.setRange(0, 100)
        self.max_per_run = QSpinBox()
        self.max_per_run.setRange(1, 100)
        self.max_per_day = QSpinBox()
        self.max_per_day.setRange(1, 200)
        self.max_fail = QSpinBox()
        self.max_fail.setRange(1, 50)
        self.delay = QSpinBox()
        self.delay.setRange(0, 600)
        self.auto_cover = QCheckBox("Automatische Anschreiben")
        self.auto_submit = QCheckBox("Automatisch absenden")
        aform.addRow("Min. Match Auto-Apply", self.min_match_apply)
        aform.addRow("Max. Bewerbungen / Lauf", self.max_per_run)
        aform.addRow("Max. Bewerbungen / Tag", self.max_per_day)
        aform.addRow("Max. Fehler / Lauf", self.max_fail)
        aform.addRow("Pause zwischen Bewerbungen (s)", self.delay)
        aform.addRow(self.auto_cover)
        aform.addRow(self.auto_submit)
        layout.addWidget(apply_box)

        # Background
        bg_box = QGroupBox("Hintergrund-Automation")
        bform = QFormLayout(bg_box)
        self.run_auto = QCheckBox("Automatisch ausführen")
        self.schedule_mode = QComboBox()
        self.schedule_mode.addItem("Bei Windows-Anmeldung", "on_login")
        self.schedule_mode.addItem("Alle X Stunden", "every_x_hours")
        self.schedule_mode.addItem("Einmal täglich", "once_daily")
        self.schedule_mode.addItem("Zweimal täglich", "twice_daily")
        self.schedule_mode.addItem("Benutzerdefinierte Zeiten", "custom")
        self.interval_hours = QSpinBox()
        self.interval_hours.setRange(1, 24)
        self.custom_times = QLineEdit()
        self.custom_times.setPlaceholderText("08:00, 17:00")
        self.paused = QCheckBox("Automation pausiert")
        bform.addRow(self.run_auto)
        bform.addRow("Zeitplan", self.schedule_mode)
        bform.addRow("Intervall (Stunden)", self.interval_hours)
        bform.addRow("Zeiten", self.custom_times)
        bform.addRow(self.paused)
        layout.addWidget(bg_box)

        # Browser
        br_box = QGroupBox("Browser")
        br_layout = QHBoxLayout(br_box)
        self.browser_status = QLabel()
        install_btn = QPushButton("Browser-Komponente installieren")
        install_btn.setObjectName("SecondaryButton")
        install_btn.clicked.connect(self.install_browser)
        br_layout.addWidget(self.browser_status, 1)
        br_layout.addWidget(install_btn)
        layout.addWidget(br_box)

        save_btn = QPushButton("Einstellungen speichern")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)
        layout.addStretch()

    def load_from_config(self) -> None:
        cfg = self.config_service.load()
        s = cfg.settings
        {
            "search_only": self.mode_search,
            "review_before_submit": self.mode_review,
            "fully_automatic": self.mode_auto,
        }.get(s.mode, self.mode_search).setChecked(True)
        self.dry_run.setChecked(bool(s.dry_run))
        enabled = set(s.enabled_sources or [])
        for key, cb in self.source_checks.items():
            cb.setChecked(key in enabled)
        self.published_days.setValue(int(s.published_within_days))
        self.min_match_dash.setValue(int(s.minimum_match_for_dashboard))
        self.max_distance.setValue(int(cfg.profile.location.max_distance_km))
        self.min_match_apply.setValue(int(s.minimum_match_for_auto_apply))
        self.max_per_run.setValue(int(s.max_applications_per_run))
        self.max_per_day.setValue(int(s.max_applications_per_day))
        self.max_fail.setValue(int(s.max_failed_applications_per_run))
        self.delay.setValue(int(s.delay_between_applications_seconds))
        self.auto_cover.setChecked(bool(getattr(s, "automatic_cover_letters", True)))
        self.auto_submit.setChecked(bool(getattr(s, "automatic_submission", False)))
        self.run_auto.setChecked(bool(s.run_automatically))
        idx = self.schedule_mode.findData(s.schedule_mode)
        self.schedule_mode.setCurrentIndex(idx if idx >= 0 else 1)
        self.interval_hours.setValue(int(s.schedule_interval_hours or 6))
        self.custom_times.setText(", ".join(s.schedule_times or []))
        self.paused.setChecked(bool(s.automation_paused))

        db = Database(cfg.db_path)
        lines = []
        for row in db.list_source_status():
            st = row.get("status") or "unknown"
            label = {
                "ok": "Aktiv",
                "error": "Fehler",
                "login_required": "Login erforderlich",
            }.get(st, st)
            msg = row.get("message") or ""
            lines.append(f"{row.get('source')}: {label}" + (f" – {msg[:80]}" if msg else ""))
        self.source_status.setText("\n".join(lines) if lines else "Noch kein Quellenstatus.")
        self.browser_status.setText(
            "Browser-Komponente: installiert" if playwright_available() else "Browser-Komponente: fehlt"
        )

    def save(self) -> None:
        cfg = self.config_service.load()
        if self.mode_search.isChecked():
            cfg.settings.mode = "search_only"
        elif self.mode_review.isChecked():
            cfg.settings.mode = "review_before_submit"
        else:
            cfg.settings.mode = "fully_automatic"
        cfg.settings.dry_run = self.dry_run.isChecked()
        cfg.settings.enabled_sources = [
            key for key, cb in self.source_checks.items() if cb.isChecked()
        ]
        cfg.settings.published_within_days = self.published_days.value()
        cfg.settings.minimum_match_for_dashboard = self.min_match_dash.value()
        cfg.profile.location.max_distance_km = float(self.max_distance.value())
        cfg.settings.minimum_match_for_auto_apply = self.min_match_apply.value()
        cfg.settings.max_applications_per_run = self.max_per_run.value()
        cfg.settings.max_applications_per_day = self.max_per_day.value()
        cfg.settings.max_failed_applications_per_run = self.max_fail.value()
        cfg.settings.delay_between_applications_seconds = self.delay.value()
        cfg.settings.automatic_cover_letters = self.auto_cover.isChecked()
        cfg.settings.automatic_submission = self.auto_submit.isChecked()
        cfg.settings.run_automatically = self.run_auto.isChecked()
        cfg.settings.schedule_mode = self.schedule_mode.currentData()
        cfg.settings.schedule_interval_hours = self.interval_hours.value()
        times = [t.strip() for t in self.custom_times.text().split(",") if t.strip()]
        cfg.settings.schedule_times = times or ["08:00"]
        cfg.settings.automation_paused = self.paused.isChecked()

        errors = self.config_service.validate(cfg)
        if errors:
            QMessageBox.warning(self, "Einstellungen", "\n".join(errors))
            return
        self.config_service.save(cfg)
        ok, msg = ScheduleService(cfg).sync_from_config()
        QMessageBox.information(self, "Einstellungen", f"Gespeichert.\n{msg}" if ok else f"Gespeichert, Zeitplan: {msg}")

    def install_browser(self) -> None:
        self.browser_status.setText("Installation läuft…")
        worker = BrowserInstallWorker()
        thread = start_worker(worker)

        def done(ok: bool, msg: str) -> None:
            self.browser_status.setText(msg)
            if ok:
                QMessageBox.information(self, "Browser", msg)
            else:
                QMessageBox.warning(self, "Browser", msg)

        worker.finished.connect(done)
        self._install_worker = worker
        self._install_thread = thread
