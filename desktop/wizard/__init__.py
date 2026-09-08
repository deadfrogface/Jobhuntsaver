"""First-run wizard."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from desktop.services import ConfigService
from desktop.widgets import ListEditor


class WelcomePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Willkommen bei Jobhuntsaver")
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Diese App sucht Jobs in Deutschland, bewertet Matches und kann "
                "optional Bewerbungen vorbereiten.\n\n"
                "Standard: Nur Suche, Dry Run an, Automation aus."
            )
        )


class PersonalPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Persönliche Daten")
        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.email = QLineEdit()
        self.phone = QLineEdit()
        form = QFormLayout(self)
        form.addRow("Vorname", self.first_name)
        form.addRow("Nachname", self.last_name)
        form.addRow("E-Mail", self.email)
        form.addRow("Telefon", self.phone)


class LocationPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Standort")
        self.address = QLineEdit()
        self.distance = QDoubleSpinBox()
        self.distance.setRange(1, 200)
        self.distance.setValue(20)
        self.distance.setSuffix(" km")
        form = QFormLayout(self)
        form.addRow("Heimatadresse", self.address)
        form.addRow("Max. Pendelweg", self.distance)


class JobsPageWizard(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Gewünschte Jobs")
        self.titles = ListEditor("Jobtitel…")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Tragen Sie gewünschte Jobtitel ein:"))
        layout.addWidget(self.titles)


class SkillsPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Skills & Erfahrung")
        self.skills = ListEditor("Skill…")
        self.languages = ListEditor("Sprache…")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Skills"))
        layout.addWidget(self.skills)
        layout.addWidget(QLabel("Sprachen"))
        layout.addWidget(self.languages)


class CVPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Lebenslauf")
        self.cv_path = ""
        self.label = QLabel("Noch kein CV gewählt (optional)")
        pick = QPushButton("CV auswählen")
        pick.clicked.connect(self._pick)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(pick)

    def _pick(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "CV", "", "Dokumente (*.pdf *.docx)"
        )
        if path:
            self.cv_path = path
            self.label.setText(path)


class ModePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Modus")
        self.search_only = QRadioButton("Nur Suche (empfohlen)")
        self.search_only.setChecked(True)
        self.review = QRadioButton("Vor Absenden prüfen")
        self.auto = QRadioButton("Vollautomatisch")
        self.dry = QCheckBox("Dry Run aktiv")
        self.dry.setChecked(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.search_only)
        layout.addWidget(self.review)
        layout.addWidget(self.auto)
        layout.addWidget(self.dry)


class FinishPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Fertig")
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Setup abgeschlossen.\n"
                "Sie können später alles unter Profil und Einstellungen ändern."
            )
        )


class FirstRunWizard(QWizard):
    def __init__(self, config_service: ConfigService, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Jobhuntsaver – Ersteinrichtung")
        self.config_service = config_service
        self.personal = PersonalPage()
        self.location = LocationPage()
        self.jobs = JobsPageWizard()
        self.skills = SkillsPage()
        self.cv = CVPage()
        self.mode = ModePage()
        self.addPage(WelcomePage())
        self.addPage(self.personal)
        self.addPage(self.location)
        self.addPage(self.jobs)
        self.addPage(self.skills)
        self.addPage(self.cv)
        self.addPage(self.mode)
        self.addPage(FinishPage())

    def accept(self) -> None:
        cfg = self.config_service.load()
        cfg = self.config_service.apply_safe_defaults(cfg)
        cfg.application.first_name = self.personal.first_name.text().strip()
        cfg.application.last_name = self.personal.last_name.text().strip()
        cfg.application.email = self.personal.email.text().strip()
        cfg.application.phone = self.personal.phone.text().strip()
        if self.location.address.text().strip():
            cfg.profile.location.home_address = self.location.address.text().strip()
        cfg.profile.location.max_distance_km = float(self.location.distance.value())
        titles = self.jobs.titles.get_items()
        if titles:
            cfg.profile.jobs.desired_titles = titles
        skills = self.skills.skills.get_items()
        if skills:
            cfg.profile.qualifications.skills = skills
        langs = self.skills.languages.get_items()
        if langs:
            from core.config import LanguageEntry

            entries = []
            for item in langs:
                if isinstance(item, LanguageEntry):
                    entries.append(item)
                else:
                    # "Englisch C1" / plain name
                    parts = str(item).rsplit(" ", 1)
                    if len(parts) == 2 and len(parts[1]) <= 3:
                        entries.append(LanguageEntry(language=parts[0], level=parts[1]))
                    else:
                        entries.append(LanguageEntry(language=str(item), level=""))
            cfg.profile.qualifications.languages = entries
        if self.mode.review.isChecked():
            cfg.settings.mode = "review_before_submit"
        elif self.mode.auto.isChecked():
            cfg.settings.mode = "fully_automatic"
        else:
            cfg.settings.mode = "search_only"
        cfg.settings.dry_run = self.mode.dry.isChecked()
        self.config_service.save(cfg)
        if self.cv.cv_path:
            self.config_service.copy_cv_into_storage(Path(self.cv.cv_path))
        self.config_service.mark_first_run_done()
        super().accept()
