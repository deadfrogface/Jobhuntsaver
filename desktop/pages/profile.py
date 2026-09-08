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
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.config import LanguageEntry
from desktop.services import ConfigService
from desktop.widgets import ListEditor
from desktop.widgets.cv_import_dialog import CvImportDialog
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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        root = QVBoxLayout(self)
        root.addWidget(scroll)
        layout = QVBoxLayout(inner)

        # Berufswünsche
        self.desired_titles = ListEditor("Gewünschter Beruf…")
        self.alt_titles = ListEditor("Alternativer Beruf…")
        self.unwanted_titles = ListEditor("Ausschluss…")
        self.desired_industries = ListEditor("Branche…")
        self.excluded_industries = ListEditor("Branche ausschließen…")
        jobs_box = QGroupBox("Berufswünsche")
        jobs_form = QFormLayout(jobs_box)
        jobs_form.addRow("Gewünschte Berufe", self.desired_titles)
        jobs_form.addRow("Alternative Berufe", self.alt_titles)
        jobs_form.addRow("Ausschlüsse", self.unwanted_titles)
        jobs_form.addRow("Branchen", self.desired_industries)
        jobs_form.addRow("Branchen ausschließen", self.excluded_industries)
        layout.addWidget(jobs_box)

        # Berufserfahrung
        self.experience = ExperienceEditor()
        exp_box = QGroupBox("Berufserfahrung")
        exp_layout = QVBoxLayout(exp_box)
        exp_layout.addWidget(self.experience)
        layout.addWidget(exp_box)

        # Ausbildung
        self.education = EducationEditor()
        edu_box = QGroupBox("Ausbildung")
        edu_layout = QVBoxLayout(edu_box)
        edu_layout.addWidget(self.education)
        layout.addWidget(edu_box)

        # Qualifikationen
        self.skills = ListEditor("Skill…")
        self.software = ListEditor("Software…")
        self.certificates = CertificateEditor()
        self.driving = ListEditor("z. B. Klasse B (PKW)")
        quals = QGroupBox("Qualifikationen")
        qform = QFormLayout(quals)
        qform.addRow("Skills", self.skills)
        qform.addRow("Software", self.software)
        qform.addRow("Zertifikate / Weiterbildungen", self.certificates)
        qform.addRow("Führerschein", self.driving)
        layout.addWidget(quals)

        # Sprachen
        self.languages = LanguageEditor()
        lang_box = QGroupBox("Sprachen")
        lang_layout = QVBoxLayout(lang_box)
        lang_layout.addWidget(self.languages)
        layout.addWidget(lang_box)

        # Standort & Arbeitsmodell
        self.home_address = QLineEdit()
        self.max_distance = QDoubleSpinBox()
        self.max_distance.setRange(1, 300)
        self.max_distance.setSuffix(" km")
        self.allow_remote = QCheckBox("Voll remote (DE) erlauben")
        self.allow_hybrid = QCheckBox("Hybrid erlauben")
        self.country = QLineEdit()
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
        pref = QGroupBox("Standort & Arbeitsmodell")
        pform = QFormLayout(pref)
        pform.addRow("Heimatadresse", self.home_address)
        pform.addRow("Max. Pendelweg", self.max_distance)
        pform.addRow(self.allow_remote)
        pform.addRow(self.allow_hybrid)
        pform.addRow("Land", self.country)
        row = QHBoxLayout()
        for w in (self.full_time, self.part_time, self.remote, self.hybrid, self.onsite):
            row.addWidget(w)
        pform.addRow("Arbeitsmodell", row)
        pform.addRow("Mindestgehalt", self.min_salary)
        pform.addRow("Bevorzugte Firmen", self.preferred_companies)
        pform.addRow("Ausgeschlossene Firmen", self.excluded_companies)
        layout.addWidget(pref)

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
            ("Führerschein (Formular)", self.drv),
            ("Arbeitserlaubnis", self.work_auth),
            ("Kündigungsfrist", self.notice),
            ("Frühester Start", self.start),
            ("Gehaltsvorstellung", self.salary_exp),
            ("Aktuelle Position", self.current_job),
            ("Ausbildung (Kurztext)", self.edu_text),
            ("Sprachen (Kurztext)", self.lang_text),
            ("Reisebereitschaft", self.travel),
            ("Umzugsbereitschaft", self.relocate),
            ("Remote-Präferenz", self.remote_pref),
        ]:
            aform.addRow(label, widget)
        layout.addWidget(app)

        # Lebenslauf
        self.cv_label = QLabel("Kein CV ausgewählt")
        cv_select = QPushButton("Lebenslauf auswählen")
        cv_select.setObjectName("SecondaryButton")
        cv_select.clicked.connect(self.select_cv)
        cv_import = QPushButton("Profil aus Lebenslauf einlesen")
        cv_import.setObjectName("PrimaryButton")
        cv_import.clicked.connect(lambda: self.import_from_cv(update=False))
        cv_update = QPushButton("Profil aus Lebenslauf aktualisieren")
        cv_update.setObjectName("SecondaryButton")
        cv_update.clicked.connect(lambda: self.import_from_cv(update=True))
        cv_box = QGroupBox("Lebenslauf")
        cv_layout = QVBoxLayout(cv_box)
        cv_layout.addWidget(self.cv_label)
        cv_row = QHBoxLayout()
        cv_row.addWidget(cv_select)
        cv_row.addWidget(cv_import)
        cv_row.addWidget(cv_update)
        cv_row.addStretch()
        cv_layout.addLayout(cv_row)
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
        self.cv_label.setText(a.cv_path or "Kein CV ausgewählt")

    def select_cv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Lebenslauf auswählen",
            "",
            "Dokumente (*.pdf *.docx);;Alle Dateien (*.*)",
        )
        if not path:
            return
        dest = self.config_service.copy_cv_into_storage(Path(path), label="Default CV")
        self.cv_label.setText(str(dest))
        QMessageBox.information(
            self,
            "Lebenslauf",
            "Lebenslauf gespeichert.\nSie können jetzt „Profil aus Lebenslauf einlesen“ nutzen.",
        )

    def import_from_cv(self, update: bool = False) -> None:
        cfg = self.config_service.load()
        cv_path = Path(cfg.application.cv_path) if cfg.application.cv_path else None
        if not cv_path or not cv_path.exists():
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Lebenslauf für Import",
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
        QMessageBox.information(self, "Lebenslauf", "Profil aktualisiert.")

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
            QMessageBox.warning(self, "Profil", "\n".join(errors))
            return
        self.config_service.save(cfg)
        QMessageBox.information(self, "Profil", "Gespeichert.")
