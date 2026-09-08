"""Profile page — human-friendly sections and CV import."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.i18n import TRANSLATIONS, tr
from desktop.services import ConfigService
from desktop.widgets import ListEditor
from desktop.widgets.cv_import_dialog import CvImportDialog
from desktop.widgets.scroll_page import wrap_scrollable
from desktop.widgets.structured_editors import (
    CertificateEditor,
    EducationEditor,
    ExperienceEditor,
    LanguageEditor,
)


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

        # Berufswünsche
        self.desired_titles = ListEditor("placeholder.job_title", visible_rows=3)
        self.alt_titles = ListEditor("placeholder.alt_title", visible_rows=3)
        self.unwanted_titles = ListEditor("placeholder.exclude", visible_rows=3)
        self.desired_industries = ListEditor("placeholder.industry", visible_rows=3)
        self.excluded_industries = ListEditor("placeholder.exclude", visible_rows=3)
        self.jobs_box = QGroupBox()
        jobs_form = QFormLayout(self.jobs_box)
        self.lbl_desired = QLabel()
        self.lbl_alt = QLabel()
        self.lbl_unwanted = QLabel()
        self.lbl_industries = QLabel()
        self.lbl_industries_ex = QLabel()
        jobs_form.addRow(self.lbl_desired, self.desired_titles)
        jobs_form.addRow(self.lbl_alt, self.alt_titles)
        jobs_form.addRow(self.lbl_unwanted, self.unwanted_titles)
        jobs_form.addRow(self.lbl_industries, self.desired_industries)
        jobs_form.addRow(self.lbl_industries_ex, self.excluded_industries)
        layout.addWidget(self.jobs_box)

        # Berufserfahrung
        self.experience = ExperienceEditor()
        self.exp_box = QGroupBox()
        exp_layout = QVBoxLayout(self.exp_box)
        exp_layout.addWidget(self.experience)
        layout.addWidget(self.exp_box)

        # Ausbildung
        self.education = EducationEditor()
        self.edu_box = QGroupBox()
        edu_layout = QVBoxLayout(self.edu_box)
        edu_layout.addWidget(self.education)
        layout.addWidget(self.edu_box)

        # Qualifikationen
        self.skills = ListEditor("placeholder.skill", visible_rows=3)
        self.software = ListEditor("placeholder.software", visible_rows=3)
        self.certificates = CertificateEditor()
        self.driving = ListEditor("placeholder.license", visible_rows=3)
        self.quals_box = QGroupBox()
        qform = QFormLayout(self.quals_box)
        self.lbl_skills = QLabel()
        self.lbl_software = QLabel()
        self.lbl_certificates = QLabel()
        self.lbl_license = QLabel()
        qform.addRow(self.lbl_skills, self.skills)
        qform.addRow(self.lbl_software, self.software)
        qform.addRow(self.lbl_certificates, self.certificates)
        qform.addRow(self.lbl_license, self.driving)
        layout.addWidget(self.quals_box)

        # Sprachen
        self.languages = LanguageEditor()
        self.lang_box = QGroupBox()
        lang_layout = QVBoxLayout(self.lang_box)
        lang_layout.addWidget(self.languages)
        layout.addWidget(self.lang_box)

        # Standort & Arbeitsmodell
        self.home_address = QLineEdit()
        self.max_distance = QDoubleSpinBox()
        self.max_distance.setRange(1, 300)
        self.max_distance.setSuffix(" km")
        self.allow_remote = QCheckBox()
        self.allow_hybrid = QCheckBox()
        self.country = QLineEdit()
        self.full_time = QCheckBox()
        self.part_time = QCheckBox()
        self.remote = QCheckBox()
        self.hybrid = QCheckBox()
        self.onsite = QCheckBox()
        self.min_salary = QDoubleSpinBox()
        self.min_salary.setRange(0, 500000)
        self.min_salary.setSuffix(" €")
        self.preferred_companies = ListEditor("placeholder.add_entry", visible_rows=3)
        self.excluded_companies = ListEditor("placeholder.add_entry", visible_rows=3)
        self.pref_box = QGroupBox()
        pform = QFormLayout(self.pref_box)
        self.lbl_home = QLabel()
        self.lbl_commute = QLabel()
        self.lbl_country = QLabel()
        self.lbl_work_model = QLabel()
        self.lbl_min_salary = QLabel()
        self.lbl_pref_companies = QLabel()
        self.lbl_ex_companies = QLabel()
        pform.addRow(self.lbl_home, self.home_address)
        pform.addRow(self.lbl_commute, self.max_distance)
        pform.addRow(self.allow_remote)
        pform.addRow(self.allow_hybrid)
        pform.addRow(self.lbl_country, self.country)
        row = QHBoxLayout()
        for w in (self.full_time, self.part_time, self.remote, self.hybrid, self.onsite):
            row.addWidget(w)
        pform.addRow(self.lbl_work_model, row)
        pform.addRow(self.lbl_min_salary, self.min_salary)
        pform.addRow(self.lbl_pref_companies, self.preferred_companies)
        pform.addRow(self.lbl_ex_companies, self.excluded_companies)
        layout.addWidget(self.pref_box)

        # Bewerbungsdaten
        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.street = QLineEdit()
        self.postal_code = QLineEdit()
        self.city = QLineEdit()
        self.app_country = QLineEdit()
        self.email = QLineEdit()
        self.phone = QLineEdit()
        self.dob = QLineEdit()
        self.drv = QLineEdit()
        self.work_auth = QLineEdit()
        self.notice = QLineEdit()
        self.start = QLineEdit()
        self.salary_exp = QLineEdit()
        self.current_job = QLineEdit()
        self.edu_text = QLineEdit()
        self.lang_text = QLineEdit()
        self.travel = QLineEdit()
        self.relocate = QLineEdit()
        self.remote_pref = QLineEdit()
        self.app_box = QGroupBox()
        aform = QFormLayout(self.app_box)
        self.app_field_labels: list[tuple[QLabel, str]] = []
        for key, widget in [
            ("field.first_name", self.first_name),
            ("field.last_name", self.last_name),
            ("field.street", self.street),
            ("field.postal", self.postal_code),
            ("field.city", self.city),
            ("field.country", self.app_country),
            ("field.email", self.email),
            ("field.phone", self.phone),
            ("field.dob", self.dob),
            ("field.license_form", self.drv),
            ("field.work_auth", self.work_auth),
            ("field.notice", self.notice),
            ("field.start", self.start),
            ("field.salary", self.salary_exp),
            ("field.current_job", self.current_job),
            ("field.edu_short", self.edu_text),
            ("field.lang_short", self.lang_text),
            ("field.travel", self.travel),
            ("field.relocate", self.relocate),
            ("field.remote_pref", self.remote_pref),
        ]:
            lbl = QLabel()
            self.app_field_labels.append((lbl, key))
            aform.addRow(lbl, widget)
        layout.addWidget(self.app_box)

        # Lebenslauf
        self.cv_label = QLabel()
        self.cv_select = QPushButton()
        self.cv_select.setObjectName("SecondaryButton")
        self.cv_select.clicked.connect(self.select_cv)
        self.cv_import = QPushButton()
        self.cv_import.setObjectName("PrimaryButton")
        self.cv_import.clicked.connect(lambda: self.import_from_cv(update=False))
        self.cv_update = QPushButton()
        self.cv_update.setObjectName("SecondaryButton")
        self.cv_update.clicked.connect(lambda: self.import_from_cv(update=True))
        self.cv_box = QGroupBox()
        cv_layout = QVBoxLayout(self.cv_box)
        cv_layout.addWidget(self.cv_label)
        cv_row = QHBoxLayout()
        cv_row.addWidget(self.cv_select)
        cv_row.addWidget(self.cv_import)
        cv_row.addWidget(self.cv_update)
        cv_row.addStretch()
        cv_layout.addLayout(cv_row)
        layout.addWidget(self.cv_box)

        self.save_btn = QPushButton()
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.save)
        layout.addWidget(self.save_btn)
        layout.addStretch()

        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.jobs_box.setTitle(tr("profile.career"))
        self.lbl_desired.setText(tr("profile.desired"))
        self.lbl_alt.setText(tr("profile.alternative"))
        self.lbl_unwanted.setText(tr("profile.excluded"))
        self.lbl_industries.setText(tr("profile.industries"))
        self.lbl_industries_ex.setText(tr("profile.industries_ex"))
        self.exp_box.setTitle(tr("profile.experience"))
        self.edu_box.setTitle(tr("profile.education"))
        self.quals_box.setTitle(tr("profile.qualifications"))
        self.lbl_skills.setText(tr("profile.skills"))
        self.lbl_software.setText(tr("profile.software"))
        self.lbl_certificates.setText(tr("profile.certificates"))
        self.lbl_license.setText(tr("profile.license"))
        self.lang_box.setTitle(tr("profile.languages"))
        self.pref_box.setTitle(tr("profile.location_work"))
        self.lbl_home.setText(tr("profile.home"))
        self.lbl_commute.setText(tr("profile.commute"))
        self.allow_remote.setText(tr("profile.allow_remote"))
        self.allow_hybrid.setText(tr("profile.allow_hybrid"))
        self.lbl_country.setText(tr("profile.country"))
        self.lbl_work_model.setText(tr("profile.work_model"))
        self.full_time.setText(tr("full_time"))
        self.part_time.setText(tr("part_time"))
        self.remote.setText(tr("remote"))
        self.hybrid.setText(tr("hybrid"))
        self.onsite.setText(tr("onsite"))
        self.lbl_min_salary.setText(tr("profile.min_salary"))
        self.lbl_pref_companies.setText(tr("profile.pref_companies"))
        self.lbl_ex_companies.setText(tr("profile.ex_companies"))
        self.app_box.setTitle(tr("profile.app_data"))
        for lbl, key in self.app_field_labels:
            lbl.setText(tr(key))
        self.cv_box.setTitle(tr("profile.cv"))
        no_cv = {table.get("profile.no_cv", "") for table in TRANSLATIONS.values()}
        if not self.cv_label.text() or self.cv_label.text() in no_cv:
            self.cv_label.setText(tr("profile.no_cv"))
        self.cv_select.setText(tr("btn.select_cv"))
        self.cv_import.setText(tr("btn.import_cv"))
        self.cv_update.setText(tr("btn.update_cv"))
        self.save_btn.setText(tr("btn.save_profile"))
        for editor in (
            self.desired_titles,
            self.alt_titles,
            self.unwanted_titles,
            self.desired_industries,
            self.excluded_industries,
            self.skills,
            self.software,
            self.driving,
            self.preferred_companies,
            self.excluded_companies,
        ):
            editor.retranslate()
        for editor in (self.experience, self.education, self.certificates, self.languages):
            if hasattr(editor, "retranslate"):
                editor.retranslate()

    def load_from_config(self) -> None:
        cfg = self.config_service.load()
        p = cfg.profile
        self.desired_titles.set_items(p.jobs.desired_titles)
        self.alt_titles.set_items(p.jobs.alternative_titles)
        self.unwanted_titles.set_items(p.jobs.unwanted_titles)
        self.desired_industries.set_items(p.jobs.desired_industries)
        self.excluded_industries.set_items(p.jobs.excluded_industries)
        self.skills.set_items(p.qualifications.skills)
        self.software.set_items(p.qualifications.software)
        self.languages.set_items(p.qualifications.languages)
        self.driving.set_items(p.qualifications.driving_license)
        self.education.set_items(p.qualifications.education)
        self.experience.set_items(p.qualifications.work_experience)
        self.certificates.set_items(p.qualifications.certificates)
        self.full_time.setChecked(p.employment.full_time)
        self.part_time.setChecked(p.employment.part_time)
        self.remote.setChecked(p.employment.remote)
        self.hybrid.setChecked(p.employment.hybrid)
        self.onsite.setChecked(p.employment.onsite)
        self.min_salary.setValue(float(p.employment.minimum_salary or 0))
        self.preferred_companies.set_items(p.filters.preferred_companies)
        self.excluded_companies.set_items(p.filters.excluded_companies)
        self.home_address.setText(p.location.home_address)
        self.max_distance.setValue(float(p.location.max_distance_km))
        self.allow_remote.setChecked(p.location.allow_remote_germany)
        self.allow_hybrid.setChecked(p.location.allow_hybrid)
        self.country.setText(p.location.country)

        a = cfg.application
        self.first_name.setText(a.first_name)
        self.last_name.setText(a.last_name)
        self.street.setText(a.street)
        self.postal_code.setText(a.postal_code)
        self.city.setText(a.city)
        self.app_country.setText(a.country or "DE")
        self.email.setText(a.email)
        self.phone.setText(a.phone)
        self.dob.setText(a.date_of_birth)
        self.drv.setText(a.driving_license)
        self.work_auth.setText(a.work_authorization)
        self.notice.setText(a.notice_period)
        self.start.setText(a.earliest_start_date)
        self.salary_exp.setText(a.salary_expectation)
        self.current_job.setText(a.current_employment)
        self.edu_text.setText(a.education)
        self.lang_text.setText(a.languages)
        self.travel.setText(a.willingness_to_travel)
        self.relocate.setText(a.willingness_to_relocate)
        self.remote_pref.setText(a.remote_preference)
        self.cv_label.setText(a.cv_path or tr("profile.no_cv"))

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
        self.cv_label.setText(str(dest))
        QMessageBox.information(
            self,
            tr("profile.cv"),
            tr("profile.cv_saved"),
        )

    def import_from_cv(self, update: bool = False) -> None:
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
            self.cv_label.setText(str(cv_path))
            cfg = self.config_service.load()

        dlg = CvImportDialog(cv_path, cfg.profile.qualifications, self)
        if update:
            for key, combo in dlg.actions.items():
                idx = combo.findData("update")
                if idx >= 0:
                    combo.setCurrentIndex(idx)
        if dlg.exec() != dlg.DialogCode.Accepted or dlg.result_quals is None:
            return
        cfg.profile.qualifications = dlg.result_quals
        # Sync short application fields when empty
        if dlg.result_quals.driving_license and not cfg.application.driving_license:
            cfg.application.driving_license = dlg.result_quals.driving_license[0]
        if dlg.result_quals.languages and not cfg.application.languages:
            cfg.application.languages = ", ".join(dlg.result_quals.language_labels())
        if dlg.result_quals.education and not cfg.application.education:
            cfg.application.education = dlg.result_quals.education[0].qualification
        if dlg.result_quals.work_experience and not cfg.application.current_employment:
            cfg.application.current_employment = dlg.result_quals.work_experience[0].title
        self.config_service.save(cfg)
        self.load_from_config()
        QMessageBox.information(self, tr("profile.cv"), tr("profile.cv_updated"))

    def save(self) -> None:
        cfg = self.config_service.load()
        p = cfg.profile
        p.jobs.desired_titles = self.desired_titles.get_items()
        p.jobs.alternative_titles = self.alt_titles.get_items()
        p.jobs.unwanted_titles = self.unwanted_titles.get_items()
        p.jobs.desired_industries = self.desired_industries.get_items()
        p.jobs.excluded_industries = self.excluded_industries.get_items()
        p.qualifications.skills = self.skills.get_items()
        p.qualifications.software = self.software.get_items()
        p.qualifications.languages = self.languages.get_items()
        p.qualifications.driving_license = self.driving.get_items()
        p.qualifications.education = self.education.get_items()
        p.qualifications.work_experience = self.experience.get_items()
        p.qualifications.certificates = self.certificates.get_items()
        p.employment.full_time = self.full_time.isChecked()
        p.employment.part_time = self.part_time.isChecked()
        p.employment.remote = self.remote.isChecked()
        p.employment.hybrid = self.hybrid.isChecked()
        p.employment.onsite = self.onsite.isChecked()
        p.employment.minimum_salary = self.min_salary.value() or None
        p.filters.preferred_companies = self.preferred_companies.get_items()
        p.filters.excluded_companies = self.excluded_companies.get_items()
        p.location.home_address = self.home_address.text().strip()
        p.location.max_distance_km = float(self.max_distance.value())
        p.location.allow_remote_germany = self.allow_remote.isChecked()
        p.location.allow_hybrid = self.allow_hybrid.isChecked()
        p.location.country = self.country.text().strip() or "DE"

        a = cfg.application
        a.first_name = self.first_name.text().strip()
        a.last_name = self.last_name.text().strip()
        a.street = self.street.text().strip()
        a.postal_code = self.postal_code.text().strip()
        a.city = self.city.text().strip()
        a.country = self.app_country.text().strip() or "DE"
        a.email = self.email.text().strip()
        a.phone = self.phone.text().strip()
        a.date_of_birth = self.dob.text().strip()
        a.driving_license = self.drv.text().strip()
        a.work_authorization = self.work_auth.text().strip()
        a.notice_period = self.notice.text().strip()
        a.earliest_start_date = self.start.text().strip()
        a.salary_expectation = self.salary_exp.text().strip()
        a.current_employment = self.current_job.text().strip()
        a.education = self.edu_text.text().strip()
        a.languages = self.lang_text.text().strip()
        a.willingness_to_travel = self.travel.text().strip()
        a.willingness_to_relocate = self.relocate.text().strip()
        a.remote_preference = self.remote_pref.text().strip()
        a.sync_address()

        errors = self.config_service.validate(cfg)
        if errors:
            QMessageBox.warning(self, tr("nav.profile"), "\n".join(errors))
            return
        self.config_service.save(cfg)
        QMessageBox.information(self, tr("nav.profile"), tr("profile.saved"))
