"""Jobs listing page."""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database import Database
from core.models import JobStatus
from desktop.services import ConfigService


class JobsPage(QWidget):
    def __init__(self, config_service: ConfigService, parent=None) -> None:
        super().__init__(parent)
        self.config_service = config_service
        self._jobs = []

        self.min_match = QSpinBox()
        self.min_match.setRange(0, 100)
        self.max_dist = QSpinBox()
        self.max_dist.setRange(1, 500)
        self.city = QLineEdit()
        self.title = QLineEdit()
        self.company = QLineEdit()
        self.source = QLineEdit()
        self.status = QComboBox()
        self.status.addItem("Alle", "")
        for s in JobStatus:
            self.status.addItem(s.value, s.value)
        self.chk_remote = QCheckBox("Remote")
        self.chk_hybrid = QCheckBox("Hybrid")
        self.chk_onsite = QCheckBox("On-site")
        self.age_days = QSpinBox()
        self.age_days.setRange(0, 90)
        self.age_days.setSpecialValueText("beliebig")

        filters = QHBoxLayout()
        for label, widget in [
            ("Min. Match", self.min_match),
            ("Max. km", self.max_dist),
            ("Stadt", self.city),
            ("Titel", self.title),
            ("Firma", self.company),
            ("Quelle", self.source),
            ("Status", self.status),
        ]:
            box = QVBoxLayout()
            box.addWidget(QLabel(label))
            box.addWidget(widget)
            filters.addLayout(box)
        filters.addWidget(self.chk_remote)
        filters.addWidget(self.chk_hybrid)
        filters.addWidget(self.chk_onsite)

        apply_btn = QPushButton("Filtern")
        apply_btn.setObjectName("PrimaryButton")
        apply_btn.clicked.connect(self.refresh)
        open_btn = QPushButton("Job öffnen")
        open_btn.setObjectName("SecondaryButton")
        open_btn.clicked.connect(self.open_selected)
        filters.addWidget(apply_btn)
        filters.addWidget(open_btn)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            [
                "Match %",
                "Titel",
                "Firma",
                "Stadt",
                "Distanz",
                "Modell",
                "Gehalt",
                "Quelle",
                "Datum",
                "Status",
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.open_selected)

        layout = QVBoxLayout(self)
        layout.addLayout(filters)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        cfg = self.config_service.load()
        self.min_match.setValue(self.min_match.value() or int(cfg.settings.minimum_match_for_dashboard))
        if self.max_dist.value() == 1 and not hasattr(self, "_dist_init"):
            self.max_dist.setValue(int(cfg.profile.location.max_distance_km))
            self._dist_init = True
        db = Database(cfg.db_path)
        remote_types = []
        if self.chk_remote.isChecked():
            remote_types.append("remote")
        if self.chk_hybrid.isChecked():
            remote_types.append("hybrid")
        if self.chk_onsite.isChecked():
            remote_types.append("onsite")
        status_val = self.status.currentData()
        jobs = db.list_jobs(
            min_match=self.min_match.value(),
            max_distance=float(self.max_dist.value()),
            statuses=[status_val] if status_val else None,
            hide_applied=cfg.settings.hide_already_applied,
            hide_duplicates=cfg.settings.hide_duplicates,
            remote_types=remote_types or None,
            company_query=self.company.text().strip() or None,
            title_query=self.title.text().strip() or None,
            city_query=self.city.text().strip() or None,
            source=self.source.text().strip() or None,
            limit=500,
        )
        self._jobs = jobs
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for job in jobs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                str(job.match_score),
                job.title,
                job.company,
                job.city,
                "" if job.distance_km is None else f"{job.distance_km:.1f}",
                job.remote_type,
                job.salary_text or "",
                job.source,
                (job.published_at or job.discovered_at or "")[:10],
                job.status,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.DisplayRole, int(job.match_score))
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()

    def open_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._jobs):
            return
        # After sorting, map via title+company is fragile; use visible cells
        title = self.table.item(row, 1).text()
        company = self.table.item(row, 2).text()
        job = next((j for j in self._jobs if j.title == title and j.company == company), None)
        if not job:
            QMessageBox.information(self, "Job", "Eintrag nicht gefunden.")
            return
        url = job.application_url or job.url
        if url:
            webbrowser.open(url)
        else:
            QMessageBox.information(self, "Job", "Keine URL vorhanden.")
