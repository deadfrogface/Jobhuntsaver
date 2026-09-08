"""Profile and application data editing."""

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
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from desktop.services import ConfigService
from desktop.widgets import ListEditor


class ProfilePage(QWidget):
    def __init__(self, config_service: ConfigService, parent=None) -> None:
        super().__init__(parent)
        self.config_service = config_service

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        root = QVBoxLayout(self)
        root.addWidget(scroll)
        layout = QVBoxLayout(inner)

        # Personal search profile
        self.desired_titles = ListEditor("Gewünschter Titel…")
        self.alt_titles = ListEditor("Alternativer Titel…")
        self.unwanted_titles = ListEditor("Ausgeschlossener Titel…")
        self.desired_industries = ListEditor("Branche…")
        self.excluded_industries = ListEditor("Ausgeschlossene Branche…")

        jobs_box = QGroupBox("Suchprofil – Jobs")
        jobs_form = QFormLayout(jobs_box)
        jobs_form.addRow("Gewünschte Titel", self.desired_titles)
        jobs_form.addRow("Alternative Titel", self.alt_titles)
        jobs_form.addRow("Ausgeschlossen", self.unwanted_titles)
        jobs_form.addRow("Branchen", self.desired_industries)
        jobs_form.addRow("Branchen aus", self.excluded_industries)
        layout.addWidget(jobs_box)

        self.skills = ListEditor("Skill…")
        self.software = ListEditor("Software…")
        self.languages = ListEditor("Sprache…")
        self.driving = ListEditor("Führerschein…")
        self.education = ListEditor("Ausbildung…")
        self.experience = ListEditor("Erfahrung…")
        quals = QGroupBox("Qualifikationen")
        qform = QFormLayout(quals)
        qform.addRow("Skills", self.skills)
        qform.addRow("Software", self.software)
        qform.addRow("Sprachen", self.languages)
        qform.addRow("Führerschein", self.driving)
        qform.addRow("Ausbildung", self.education)
        qform.addRow("Berufserfahrung", self.experience)
        layout.addWidget(quals)

        self.full_time = QCheckBox("Vollzeit")
        self.part_time = QCheckBox("Teilzeit")
        self.remote = QCheckBox("Remote")
        self.hybrid = QCheckBox("Hybrid")
        self.onsite = QCheckBox("Vor Ort")
        self.min_salary = QDoubleSpinBox()
        self.min_salary.setRange(0, 500000)
        self.min_salary.setSuffix(" €")
        self.preferred_companies = ListEditor("Bevorzugte Firma…")
        self.excluded_companies = ListEditor("Ausgeschlossene Firma…")
        emp = QGroupBox("Job-Präferenzen")
        eform = QFormLayout(emp)
        row = QHBoxLayout()
        for w in (self.full_time, self.part_time, self.remote, self.hybrid, self.onsite):
            row.addWidget(w)
        eform.addRow("Arbeitsmodell", row)
        eform.addRow("Mindestgehalt", self.min_salary)
        eform.addRow("Bevorzugte Firmen", self.preferred_companies)
        eform.addRow("Ausgeschlossene Firmen", self.excluded_companies)
        layout.addWidget(emp)

        # Location
        self.home_address = QLineEdit()
        self.max_distance = QDoubleSpinBox()
        self.max_distance.setRange(1, 300)
        self.max_distance.setSuffix(" km")
        self.allow_remote = QCheckBox("Voll remote (DE) erlauben")
        self.allow_hybrid = QCheckBox("Hybrid erlauben")
        self.country = QLineEdit()
        loc = QGroupBox("Standort")
        lform = QFormLayout(loc)
        lform.addRow("Heimatadresse", self.home_address)
        lform.addRow("Max. Pendelweg", self.max_distance)
        lform.addRow(self.allow_remote)
        lform.addRow(self.allow_hybrid)
        lform.addRow("Land", self.country)
        layout.addWidget(loc)

        # Application data
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

        app = QGroupBox("Bewerbungsdaten")
        aform = QFormLayout(app)
        for label, widget in [
            ("Vorname", self.first_name),
            ("Nachname", self.last_name),
            ("Straße", self.street),
            ("PLZ", self.postal_code),
            ("Ort", self.city),
            ("Land", self.app_country),
            ("E-Mail", self.email),
            ("Telefon", self.phone),
            ("Geburtsdatum", self.dob),
            ("Führerschein", self.drv),
            ("Arbeitserlaubnis", self.work_auth),
            ("Kündigungsfrist", self.notice),
            ("Frühester Start", self.start),
            ("Gehaltsvorstellung", self.salary_exp),
            ("Aktuelle Position", self.current_job),
            ("Ausbildung", self.edu_text),
            ("Sprachen", self.lang_text),
            ("Reisebereitschaft", self.travel),
            ("Umzugsbereitschaft", self.relocate),
            ("Remote-Präferenz", self.remote_pref),
        ]:
            aform.addRow(label, widget)
        layout.addWidget(app)

        # CV
        self.cv_label = QLabel("Kein CV ausgewählt")
        cv_btn = QPushButton("CV auswählen")
        cv_btn.setObjectName("PrimaryButton")
        cv_btn.clicked.connect(self.select_cv)
        cv_box = QGroupBox("Lebenslauf")
        cv_layout = QHBoxLayout(cv_box)
        cv_layout.addWidget(self.cv_label, 1)
        cv_layout.addWidget(cv_btn)
        layout.addWidget(cv_box)

        save_btn = QPushButton("Profil speichern")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)
        layout.addStretch()

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
        self.cv_label.setText(a.cv_path or "Kein CV ausgewählt")

    def select_cv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "CV auswählen",
            "",
            "Dokumente (*.pdf *.docx);;Alle Dateien (*.*)",
        )
        if not path:
            return
        dest = self.config_service.copy_cv_into_storage(Path(path), label="Default CV")
        self.cv_label.setText(str(dest))
        QMessageBox.information(self, "CV", "CV gespeichert.")

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
        a.work_experience = ""
        a.languages = self.lang_text.text().strip()
        a.willingness_to_travel = self.travel.text().strip()
        a.willingness_to_relocate = self.relocate.text().strip()
        a.remote_preference = self.remote_pref.text().strip()
        a.sync_address()

        errors = self.config_service.validate(cfg)
        if errors:
            QMessageBox.warning(self, "Profil", "\n".join(errors))
            return
        self.config_service.save(cfg)
        QMessageBox.information(self, "Profil", "Gespeichert.")
