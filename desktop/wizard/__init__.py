"""First-run wizard."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from desktop.i18n import tr
from desktop.services import ConfigService
from desktop.widgets import ListEditor
from desktop.widgets.scroll_page import wrap_scrollable


def _scroll_page_body(inner: QWidget) -> QScrollArea:
    return wrap_scrollable(inner, min_content_width=480)


class WelcomePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.addWidget(self.body)
        layout.addStretch()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll_page_body(inner))
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setTitle(tr("wizard.welcome_title"))
        self.body.setText(tr("wizard.welcome_body"))


class PersonalPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.email = QLineEdit()
        self.phone = QLineEdit()
        self.lbl_first = QLabel()
        self.lbl_last = QLabel()
        self.lbl_email = QLabel()
        self.lbl_phone = QLabel()
        inner = QWidget()
        form = QFormLayout(inner)
        form.addRow(self.lbl_first, self.first_name)
        form.addRow(self.lbl_last, self.last_name)
        form.addRow(self.lbl_email, self.email)
        form.addRow(self.lbl_phone, self.phone)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll_page_body(inner))
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setTitle(tr("wizard.personal"))
        self.lbl_first.setText(tr("wizard.first_name"))
        self.lbl_last.setText(tr("wizard.last_name"))
        self.lbl_email.setText(tr("wizard.email"))
        self.lbl_phone.setText(tr("wizard.phone"))


class LocationPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.address = QLineEdit()
        self.distance = QDoubleSpinBox()
        self.distance.setRange(1, 200)
        self.distance.setValue(20)
        self.distance.setSuffix(" km")
        self.lbl_address = QLabel()
        self.lbl_distance = QLabel()
        inner = QWidget()
        form = QFormLayout(inner)
        form.addRow(self.lbl_address, self.address)
        form.addRow(self.lbl_distance, self.distance)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll_page_body(inner))
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setTitle(tr("wizard.location"))
        self.lbl_address.setText(tr("wizard.address"))
        self.lbl_distance.setText(tr("wizard.distance"))


class JobsPageWizard(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.titles = ListEditor("placeholder.job_title", visible_rows=3)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.addWidget(self.hint)
        layout.addWidget(self.titles)
        layout.addStretch()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll_page_body(inner))
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setTitle(tr("wizard.jobs"))
        self.hint.setText(tr("wizard.jobs_hint"))
        self.titles.retranslate()


class SkillsPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.lbl_skills = QLabel()
        self.lbl_languages = QLabel()
        self.skills = ListEditor("placeholder.skill", visible_rows=3)
        self.languages = ListEditor("placeholder.add_entry", visible_rows=3)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.addWidget(self.lbl_skills)
        layout.addWidget(self.skills)
        layout.addWidget(self.lbl_languages)
        layout.addWidget(self.languages)
        layout.addStretch()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll_page_body(inner))
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setTitle(tr("wizard.skills"))
        self.lbl_skills.setText(tr("profile.skills"))
        self.lbl_languages.setText(tr("profile.languages"))
        self.skills.retranslate()
        self.languages.retranslate()


class CVPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.cv_path = ""
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.pick = QPushButton()
        self.pick.clicked.connect(self._pick)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.addWidget(self.label)
        layout.addWidget(self.pick)
        layout.addStretch()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll_page_body(inner))
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setTitle(tr("wizard.cv"))
        self.pick.setText(tr("btn.select_cv"))
        if not self.cv_path:
            self.label.setText(tr("wizard.cv_none"))

    def _pick(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("wizard.cv"), "", "Dokumente (*.pdf *.docx)"
        )
        if path:
            self.cv_path = path
            self.label.setText(path)


class ModePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.search_only = QRadioButton()
        self.search_only.setChecked(True)
        self.review = QRadioButton()
        self.auto = QRadioButton()
        self.dry = QCheckBox()
        self.dry.setChecked(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.addWidget(self.search_only)
        layout.addWidget(self.review)
        layout.addWidget(self.auto)
        layout.addWidget(self.dry)
        layout.addStretch()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll_page_body(inner))
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setTitle(tr("wizard.mode"))
        self.search_only.setText(tr("settings.mode.search"))
        self.review.setText(tr("settings.mode.review"))
        self.auto.setText(tr("settings.mode.auto"))
        self.dry.setText(tr("settings.dry_run"))


class FinishPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.body = QLabel()
        self.body.setWordWrap(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.addWidget(self.body)
        layout.addStretch()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll_page_body(inner))
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setTitle(tr("wizard.finish"))
        self.body.setText(tr("wizard.finish_body"))


class FirstRunWizard(QWizard):
    def __init__(self, config_service: ConfigService, parent=None) -> None:
        super().__init__(parent)
        self.config_service = config_service
        self.setMinimumSize(640, 480)
        self.setSizeGripEnabled(True)
        self.welcome = WelcomePage()
        self.personal = PersonalPage()
        self.location = LocationPage()
        self.jobs = JobsPageWizard()
        self.skills = SkillsPage()
        self.cv = CVPage()
        self.mode = ModePage()
        self.finish = FinishPage()
        self.addPage(self.welcome)
        self.addPage(self.personal)
        self.addPage(self.location)
        self.addPage(self.jobs)
        self.addPage(self.skills)
        self.addPage(self.cv)
        self.addPage(self.mode)
        self.addPage(self.finish)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("app.name"))
        for page in (
            self.welcome,
            self.personal,
            self.location,
            self.jobs,
            self.skills,
            self.cv,
            self.mode,
            self.finish,
        ):
            if hasattr(page, "retranslate_ui"):
                page.retranslate_ui()

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
