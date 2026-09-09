"""Profile page — orchestrates section widgets and CV import/reset."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.i18n import TRANSLATIONS, tr
from desktop.pages.profile_sections import (
    ApplicantSection,
    CareerSection,
    CvSection,
    EducationSection,
    ExperienceSection,
    LanguagesSection,
    LocationWorkSection,
    QualificationsSection,
)
from desktop.services import ConfigService
from desktop.services.profile_merge import clear_cv_personal, keep_manual_qualifications
from desktop.widgets.cv_import_dialog import CvImportDialog
from desktop.widgets.scroll_page import wrap_scrollable


class ProfilePage(QWidget):
    def __init__(self, config_service: ConfigService, parent=None) -> None:
        super().__init__(parent)
        self.config_service = config_service

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(8, 8, 16, 16)
        layout.setSpacing(14)
        outer.addWidget(wrap_scrollable(inner))

        self.career = CareerSection()
        self.experience = ExperienceSection()
        self.education = EducationSection()
        self.qualifications = QualificationsSection()
        self.languages = LanguagesSection()
        self.location_work = LocationWorkSection()
        self.applicant = ApplicantSection()
        self.cv = CvSection()
        self.cv.cv_select.clicked.connect(self.select_cv)
        self.cv.cv_import.clicked.connect(self.import_from_cv)
        self.cv.cv_reset.clicked.connect(self.reset_profile)

        for section in (
            self.career,
            self.experience,
            self.education,
            self.qualifications,
            self.languages,
            self.location_work,
            self.applicant,
            self.cv,
        ):
            layout.addWidget(section)

        self.save_btn = QPushButton()
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.save)
        layout.addWidget(self.save_btn)
        layout.addStretch()

        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        no_cv = {table.get("profile.no_cv", "") for table in TRANSLATIONS.values()}
        self.career.retranslate()
        self.experience.retranslate()
        self.education.retranslate()
        self.qualifications.retranslate()
        self.languages.retranslate()
        self.location_work.retranslate()
        self.applicant.retranslate()
        self.cv.retranslate(no_cv_tokens=no_cv)
        self.save_btn.setText(tr("btn.save_profile"))

    def load_from_config(self) -> None:
        cfg = self.config_service.load()
        p = cfg.profile
        self.career.load(p.jobs)
        self.experience.load(p.qualifications)
        self.education.load(p.qualifications)
        self.qualifications.load(p.qualifications)
        self.languages.load(p.qualifications)
        self.location_work.load(p.location, p.employment, p.filters)
        self.applicant.load(
            cfg.application,
            sync_address_to_search=self.config_service.get_sync_address_to_search(),
        )
        self.cv.cv_label.setText(cfg.application.cv_path or tr("profile.no_cv"))

    def select_cv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("btn.select_cv"),
            "",
            "Dokumente (*.pdf *.docx);;Alle Dateien (*.*)",
        )
        if not path:
            return
        dest = self.config_service.copy_cv_into_storage(Path(path), label="Default CV")
        self.cv.cv_label.setText(str(dest))
        QMessageBox.information(self, tr("profile.cv"), tr("profile.cv_saved"))

    def import_from_cv(self) -> None:
        cfg = self.config_service.load()
        cv_path = Path(cfg.application.cv_path) if cfg.application.cv_path else None
        if not cv_path or not cv_path.exists():
            path, _ = QFileDialog.getOpenFileName(
                self,
                tr("btn.import_cv"),
                "",
                "Dokumente (*.pdf *.docx)",
            )
            if not path:
                return
            cv_path = self.config_service.copy_cv_into_storage(Path(path))
            self.cv.cv_label.setText(str(cv_path))
            cfg = self.config_service.load()

        dlg = CvImportDialog(cv_path, cfg.profile.qualifications, cfg.application, self)
        if dlg.exec() != dlg.DialogCode.Accepted or dlg.result_quals is None:
            return
        cfg.profile.qualifications = dlg.result_quals
        if dlg.result_application is not None:
            cfg.application = dlg.result_application
        cfg.application.cv_path = str(cv_path)
        self.config_service.save(cfg)
        self.load_from_config()
        QMessageBox.information(self, tr("profile.cv"), tr("profile.cv_updated"))

    def reset_profile(self) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle(tr("profile.reset_title"))
        msg.setText(tr("profile.reset"))
        msg.setInformativeText(tr("profile.reset_confirm_cv"))
        cv_btn = msg.addButton(tr("profile.reset_cv_only"), QMessageBox.ButtonRole.AcceptRole)
        all_btn = msg.addButton(tr("profile.reset_all"), QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked is None or clicked == msg.button(QMessageBox.StandardButton.Cancel):
            return
        if clicked is all_btn:
            confirm = QMessageBox.question(
                self,
                tr("profile.reset_title"),
                tr("profile.reset_confirm_all"),
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            self.config_service.reset_to_empty_profile(clear_search_prefs=False)
        elif clicked is cv_btn:
            confirm = QMessageBox.question(
                self,
                tr("profile.reset_title"),
                tr("profile.reset_confirm_cv"),
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            self.config_service.clear_cv_storage()
            cfg = self.config_service.load()
            cfg.profile.qualifications = keep_manual_qualifications(cfg.profile.qualifications)
            cfg.application = clear_cv_personal(cfg.application)
            cfg.application.cv_path = ""
            self.config_service.save(cfg)
        else:
            return
        self.load_from_config()
        QMessageBox.information(self, tr("profile.reset_title"), tr("profile.reset_done"))

    def save(self) -> None:
        cfg = self.config_service.load()
        p = cfg.profile
        self.career.save_into(p.jobs)
        self.experience.save_into(p.qualifications)
        self.education.save_into(p.qualifications)
        self.qualifications.save_into(p.qualifications)
        self.languages.save_into(p.qualifications)
        self.location_work.save_into(p.location, p.employment, p.filters)

        a = cfg.application
        sync_addr = self.applicant.save_into(a)
        self.config_service.set_sync_address_to_search(sync_addr)
        if sync_addr:
            parts = [
                part
                for part in (
                    a.street.strip(),
                    f"{a.postal_code} {a.city}".strip(),
                    (a.country or "").strip(),
                )
                if part
            ]
            if parts:
                p.location.home_address = ", ".join(parts)
                self.location_work.home_address.setText(p.location.home_address)

        errors = self.config_service.validate(cfg)
        if errors:
            QMessageBox.warning(self, tr("nav.profile"), "\n".join(errors))
            return
        self.config_service.save(cfg)
        QMessageBox.information(self, tr("nav.profile"), tr("profile.saved"))
