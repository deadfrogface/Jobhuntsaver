"""Applications history and review queue."""

from __future__ import annotations

import webbrowser

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database import Database
from core.models import JobStatus
from desktop.services import ConfigService


STATUS_FILTERS = [
    "",
    JobStatus.QUEUED.value,
    JobStatus.APPLYING.value,
    JobStatus.APPLIED.value,
    JobStatus.NEEDS_REVIEW.value,
    JobStatus.CAPTCHA.value,
    JobStatus.FAILED.value,
    JobStatus.CLOSED.value,
]


class ApplicationsPage(QWidget):
    def __init__(self, config_service: ConfigService, parent=None) -> None:
        super().__init__(parent)
        self.config_service = config_service
        self._records = []

        self.status = QComboBox()
        self.status.addItem("Alle", "")
        for s in STATUS_FILTERS:
            if s:
                self.status.addItem(s, s)

        refresh_btn = QPushButton("Aktualisieren")
        refresh_btn.setObjectName("PrimaryButton")
        refresh_btn.clicked.connect(self.refresh)
        open_btn = QPushButton("Manuell öffnen")
        open_btn.setObjectName("SecondaryButton")
        open_btn.clicked.connect(self.open_selected)
        review_btn = QPushButton("Nur Needs Review")
        review_btn.setObjectName("SecondaryButton")
        review_btn.clicked.connect(self.show_review_only)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Status"))
        bar.addWidget(self.status)
        bar.addWidget(refresh_btn)
        bar.addWidget(open_btn)
        bar.addWidget(review_btn)
        bar.addStretch()

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "Datum",
                "Firma",
                "Titel",
                "ATS",
                "Match",
                "Status",
                "CV",
                "Anschreiben",
                "Fehler / Grund",
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(self.table)

    def show_review_only(self) -> None:
        idx = self.status.findData(JobStatus.NEEDS_REVIEW.value)
        if idx >= 0:
            self.status.setCurrentIndex(idx)
        self.refresh()

    def refresh(self) -> None:
        cfg = self.config_service.load()
        db = Database(cfg.db_path)
        status_val = self.status.currentData()
        records = db.list_applications(
            statuses=[status_val] if status_val else None,
            limit=500,
        )
        self._records = records
        self.table.setRowCount(0)
        for rec in records:
            job = db.get_job(rec.job_id) if rec.job_id else None
            match = str(job.match_score) if job else ""
            ats = (job.ats_type if job else "") or rec.platform
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                (rec.application_date or "")[:19],
                rec.company,
                rec.position,
                ats,
                match,
                rec.status,
                rec.cv_used,
                "ja" if rec.cover_letter_used else "",
                rec.error_message or rec.result or "",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()

    def open_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._records):
            return
        rec = self._records[row]
        cfg = self.config_service.load()
        db = Database(cfg.db_path)
        job = db.get_job(rec.job_id) if rec.job_id else None
        url = ""
        if job:
            url = job.application_url or job.url
        if url:
            webbrowser.open(url)
        else:
            QMessageBox.information(self, "Bewerbung", "Keine Bewerbungs-URL vorhanden.")
