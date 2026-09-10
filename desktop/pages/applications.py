"""Applications history and review queue."""

from __future__ import annotations

import webbrowser

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
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
from desktop.i18n import tr
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
        self.status.addItem("", "")
        for s in STATUS_FILTERS:
            if s:
                self.status.addItem(s, s)

        self.lbl_status = QLabel()
        self.refresh_btn = QPushButton()
        self.refresh_btn.setObjectName("PrimaryButton")
        self.refresh_btn.clicked.connect(self.refresh)
        self.open_btn = QPushButton()
        self.open_btn.setObjectName("SecondaryButton")
        self.open_btn.clicked.connect(self.open_selected)
        self.preview_btn = QPushButton()
        self.preview_btn.setObjectName("SecondaryButton")
        self.preview_btn.clicked.connect(self.preview_selected)
        self.review_btn = QPushButton()
        self.review_btn.setObjectName("SecondaryButton")
        self.review_btn.clicked.connect(self.show_review_only)

        filter_form = QFormLayout()
        filter_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        filter_form.addRow(self.lbl_status, self.status)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.refresh_btn)
        btn_row.addWidget(self.open_btn)
        btn_row.addWidget(self.preview_btn)
        btn_row.addWidget(self.review_btn)
        btn_row.addStretch()
        filter_form.addRow(btn_row)

        self.table = QTableWidget(0, 9)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        for col in (0, 3, 4, 5, 6, 7):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)

        layout = QVBoxLayout(self)
        layout.addLayout(filter_form)
        layout.addWidget(self.table)

        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.lbl_status.setText(tr("jobs.status"))
        self.status.setItemText(0, tr("jobs.all"))
        self.refresh_btn.setText(tr("btn.refresh"))
        self.open_btn.setText(tr("btn.open_manual"))
        self.preview_btn.setText(tr("btn.preview_apply"))
        self.review_btn.setText(tr("btn.review_only"))
        self.table.setHorizontalHeaderLabels(
            [
                tr("apps.date"),
                tr("jobs.company"),
                tr("jobs.title"),
                tr("apps.ats"),
                tr("apps.match"),
                tr("jobs.status"),
                tr("apps.cv"),
                tr("apps.cover"),
                tr("apps.error"),
            ]
        )

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
            QMessageBox.information(
                self, tr("nav.applications"), "Keine Bewerbungs-URL vorhanden."
            )

    def preview_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._records):
            return
        rec = self._records[row]
        cfg = self.config_service.load()
        db = Database(cfg.db_path)
        job = db.get_job(rec.job_id) if rec.job_id else None
        if job is None:
            # Fallback: show stored error/preview text from application record
            from desktop.widgets.apply_preview_dialog import ApplyPreviewDialog
            from apply.preview import ApplicationPreview

            preview = ApplicationPreview(
                job_id=rec.job_id,
                company=rec.company,
                title=rec.position,
                application_url="",
                ats=rec.platform or "unknown",
                ats_support="unknown",
                ats_note=rec.error_message or "",
                dry_run=bool(cfg.settings.dry_run),
                mode=cfg.settings.mode,
                will_submit=False,
                form_values={},
                documents={"CV": rec.cv_used, "Anschreiben": rec.cover_letter_used},
                cover_letter_preview=rec.error_message or "",
                warnings=["Job-Datensatz nicht gefunden — gespeicherte Notiz wird angezeigt."],
            )
            ApplyPreviewDialog(preview, self).exec()
            return
        from apply.preview import build_application_preview
        from desktop.widgets.apply_preview_dialog import ApplyPreviewDialog

        preview = build_application_preview(job, cfg)
        ApplyPreviewDialog(preview, self).exec()
