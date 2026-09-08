"""Jobs listing page."""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
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
from desktop.i18n import tr
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
        self.status.addItem("", "")
        for s in JobStatus:
            self.status.addItem(s.value, s.value)
        self.chk_remote = QCheckBox()
        self.chk_hybrid = QCheckBox()
        self.chk_onsite = QCheckBox()
        self.age_days = QSpinBox()
        self.age_days.setRange(0, 90)

        self.lbl_min_match = QLabel()
        self.lbl_max_dist = QLabel()
        self.lbl_city = QLabel()
        self.lbl_title = QLabel()
        self.lbl_company = QLabel()
        self.lbl_source = QLabel()
        self.lbl_status = QLabel()

        filter_form = QFormLayout()
        filter_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        filter_form.addRow(self.lbl_min_match, self.min_match)
        filter_form.addRow(self.lbl_max_dist, self.max_dist)
        filter_form.addRow(self.lbl_city, self.city)
        filter_form.addRow(self.lbl_title, self.title)
        filter_form.addRow(self.lbl_company, self.company)
        filter_form.addRow(self.lbl_source, self.source)
        filter_form.addRow(self.lbl_status, self.status)

        model_row = QHBoxLayout()
        model_row.addWidget(self.chk_remote)
        model_row.addWidget(self.chk_hybrid)
        model_row.addWidget(self.chk_onsite)
        model_row.addStretch()
        filter_form.addRow(model_row)

        self.apply_btn = QPushButton()
        self.apply_btn.setObjectName("PrimaryButton")
        self.apply_btn.clicked.connect(self.refresh)
        self.open_btn = QPushButton()
        self.open_btn.setObjectName("SecondaryButton")
        self.open_btn.clicked.connect(self.open_selected)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.apply_btn)
        btn_row.addWidget(self.open_btn)
        btn_row.addStretch()
        filter_form.addRow(btn_row)

        self.table = QTableWidget(0, 10)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.open_selected)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        for col in (0, 3, 4, 5, 6, 7, 8, 9):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout = QVBoxLayout(self)
        layout.addLayout(filter_form)
        layout.addWidget(self.table)

        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.lbl_min_match.setText(tr("jobs.min_match"))
        self.lbl_max_dist.setText(tr("jobs.max_km"))
        self.lbl_city.setText(tr("jobs.city"))
        self.lbl_title.setText(tr("jobs.title"))
        self.lbl_company.setText(tr("jobs.company"))
        self.lbl_source.setText(tr("jobs.source"))
        self.lbl_status.setText(tr("jobs.status"))
        self.chk_remote.setText(tr("remote"))
        self.chk_hybrid.setText(tr("hybrid"))
        self.chk_onsite.setText(tr("onsite"))
        self.apply_btn.setText(tr("btn.filter"))
        self.open_btn.setText(tr("btn.open_job"))
        self.status.setItemText(0, tr("jobs.all"))
        self.table.setHorizontalHeaderLabels(
            [
                tr("col.match"),
                tr("col.title"),
                tr("col.company"),
                tr("col.city"),
                tr("col.distance"),
                tr("col.model"),
                tr("col.salary"),
                tr("col.source"),
                tr("col.date"),
                tr("col.status"),
            ]
        )

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

    def open_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._jobs):
            return
        # After sorting, map via title+company is fragile; use visible cells
        title = self.table.item(row, 1).text()
        company = self.table.item(row, 2).text()
        job = next((j for j in self._jobs if j.title == title and j.company == company), None)
        if not job:
            QMessageBox.information(self, tr("nav.jobs"), "Eintrag nicht gefunden.")
            return
        url = job.application_url or job.url
        if url:
            webbrowser.open(url)
        else:
            QMessageBox.information(self, tr("nav.jobs"), "Keine URL vorhanden.")
