"""CV import confirmation dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from core.config import QualificationsConfig
from core.cv_parser import import_cv, parsed_to_qualifications
from desktop.services.profile_merge import Action, merge_qualifications, summarize_incoming


class CvImportDialog(QDialog):
    def __init__(
        self,
        cv_path: Path,
        existing: QualificationsConfig,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Profil aus Lebenslauf")
        self.resize(720, 560)
        self.existing = existing
        self.incoming: QualificationsConfig | None = None
        self.result_quals: QualificationsConfig | None = None

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.actions: dict[str, QComboBox] = {}
        form = QFormLayout()
        for key, label in [
            ("languages", "Sprachen"),
            ("education", "Ausbildung"),
            ("work_experience", "Berufserfahrung"),
            ("certificates", "Zertifikate / Weiterbildung"),
            ("software", "Software"),
            ("skills", "Skills"),
            ("driving_license", "Führerschein"),
        ]:
            box = QComboBox()
            box.addItem("Neu hinzufügen (ohne Duplikate)", "add")
            box.addItem("Vorhandene aktualisieren", "update")
            box.addItem("Bestehende behalten", "keep")
            box.addItem("Ignorieren", "ignore")
            self.actions[key] = box
            form.addRow(label, box)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Erkannte Angaben aus dem Lebenslauf. Bitte prüfen und bestätigen.\n"
                "Es wird nichts erfunden — unsichere Felder bleiben leer."
            )
        )
        layout.addWidget(self.preview, 1)
        layout.addLayout(form)
        layout.addWidget(buttons)

        try:
            parsed = import_cv(cv_path)
            self.incoming = parsed_to_qualifications(parsed)
            summary = summarize_incoming(self.incoming)
            lines = [f"Datei: {cv_path.name}", ""]
            for key, label in [
                ("languages", "Sprachen"),
                ("driving_license", "Führerschein"),
                ("education", "Ausbildung"),
                ("work_experience", "Berufserfahrung"),
                ("certificates", "Zertifikate"),
                ("software", "Software"),
                ("skills", "Skills"),
            ]:
                items = summary.get(key) or []
                lines.append(f"=== {label} ({len(items)}) ===")
                if not items:
                    lines.append("(nichts erkannt)")
                else:
                    lines.extend(f"• {item}" for item in items)
                lines.append("")
            self.preview.setPlainText("\n".join(lines))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Lebenslauf", f"Konnte nicht gelesen werden:\n{exc}")
            self.preview.setPlainText(str(exc))

    def _accept(self) -> None:
        if self.incoming is None:
            self.reject()
            return
        kwargs = {key: combo.currentData() for key, combo in self.actions.items()}
        self.result_quals = merge_qualifications(self.existing, self.incoming, **kwargs)
        self.accept()
