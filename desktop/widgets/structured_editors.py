"""Structured profile editors (languages, education, experience, certificates)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.config import (
    CertificateEntry,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
)


class _EntryListEditor(QWidget):
    """List with add/edit/remove opening a dialog."""

    def __init__(self, empty_hint: str, parent=None) -> None:
        super().__init__(parent)
        self.list = QListWidget()
        self._items: list = []
        add_btn = QPushButton("Hinzufügen")
        edit_btn = QPushButton("Bearbeiten")
        remove_btn = QPushButton("Entfernen")
        for b in (add_btn, edit_btn, remove_btn):
            b.setObjectName("SecondaryButton")
        add_btn.clicked.connect(self._add)
        edit_btn.clicked.connect(self._edit)
        remove_btn.clicked.connect(self._remove)
        row = QHBoxLayout()
        row.addWidget(add_btn)
        row.addWidget(edit_btn)
        row.addWidget(remove_btn)
        row.addStretch()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(empty_hint))
        layout.addWidget(self.list)
        layout.addLayout(row)

    def _refresh(self) -> None:
        self.list.clear()
        for item in self._items:
            self.list.addItem(item.label() if hasattr(item, "label") else str(item))

    def _add(self) -> None:
        item = self.create_item()
        if item is None:
            return
        self._items.append(item)
        self._refresh()

    def _edit(self) -> None:
        row = self.list.currentRow()
        if row < 0 or row >= len(self._items):
            return
        item = self.edit_item(self._items[row])
        if item is None:
            return
        self._items[row] = item
        self._refresh()

    def _remove(self) -> None:
        row = self.list.currentRow()
        if row < 0:
            return
        self._items.pop(row)
        self._refresh()

    def create_item(self):
        raise NotImplementedError

    def edit_item(self, existing):
        raise NotImplementedError

    def get_items(self) -> list:
        return list(self._items)

    def set_items(self, items: list | None) -> None:
        self._items = list(items or [])
        self._refresh()


class LanguageEditor(_EntryListEditor):
    def __init__(self, parent=None) -> None:
        super().__init__("Sprache und Niveau (z. B. Englisch | C1)", parent)

    def create_item(self):
        return self._dialog()

    def edit_item(self, existing: LanguageEntry):
        return self._dialog(existing)

    def _dialog(self, existing: LanguageEntry | None = None) -> LanguageEntry | None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Sprache")
        lang = QLineEdit(existing.language if existing else "")
        level = QLineEdit(existing.level if existing else "")
        level.setPlaceholderText("C1 / C2 / B2 …")
        form = QFormLayout()
        form.addRow("Sprache", lang)
        form.addRow("Niveau", level)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout = QVBoxLayout(dlg)
        layout.addLayout(form)
        layout.addWidget(buttons)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        if not lang.text().strip():
            return None
        return LanguageEntry(language=lang.text().strip(), level=level.text().strip())


class EducationEditor(_EntryListEditor):
    def __init__(self, parent=None) -> None:
        super().__init__("Ausbildung / Schule", parent)

    def create_item(self):
        return self._dialog()

    def edit_item(self, existing: EducationEntry):
        return self._dialog(existing)

    def _dialog(self, existing: EducationEntry | None = None) -> EducationEntry | None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Ausbildung")
        fields = {
            "qualification": QLineEdit(existing.qualification if existing else ""),
            "institution": QLineEdit(existing.institution if existing else ""),
            "location": QLineEdit(existing.location if existing else ""),
            "start_date": QLineEdit(existing.start_date if existing else ""),
            "end_date": QLineEdit(existing.end_date if existing else ""),
            "completion_date": QLineEdit(existing.completion_date if existing else ""),
        }
        form = QFormLayout()
        form.addRow("Abschluss / Qualifikation", fields["qualification"])
        form.addRow("Einrichtung / Firma", fields["institution"])
        form.addRow("Ort", fields["location"])
        form.addRow("Beginn", fields["start_date"])
        form.addRow("Ende", fields["end_date"])
        form.addRow("Abschlussdatum", fields["completion_date"])
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout = QVBoxLayout(dlg)
        layout.addLayout(form)
        layout.addWidget(buttons)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        entry = EducationEntry(**{k: w.text().strip() for k, w in fields.items()})
        if not entry.qualification and not entry.institution:
            return None
        return entry


class ExperienceEditor(_EntryListEditor):
    def __init__(self, parent=None) -> None:
        super().__init__("Berufserfahrung", parent)

    def create_item(self):
        return self._dialog()

    def edit_item(self, existing: ExperienceEntry):
        return self._dialog(existing)

    def _dialog(self, existing: ExperienceEntry | None = None) -> ExperienceEntry | None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Berufserfahrung")
        title = QLineEdit(existing.title if existing else "")
        company = QLineEdit(existing.company if existing else "")
        location = QLineEdit(existing.location if existing else "")
        start = QLineEdit(existing.start_date if existing else "")
        end = QLineEdit(existing.end_date if existing else "")
        resp = QPlainTextEdit()
        if existing:
            resp.setPlainText("\n".join(existing.responsibilities))
        resp.setPlaceholderText("Eine Aufgabe pro Zeile")
        form = QFormLayout()
        form.addRow("Position", title)
        form.addRow("Firma", company)
        form.addRow("Ort", location)
        form.addRow("Beginn", start)
        form.addRow("Ende / aktuell", end)
        form.addRow("Aufgaben", resp)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout = QVBoxLayout(dlg)
        layout.addLayout(form)
        layout.addWidget(buttons)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        responsibilities = [
            ln.strip(" -•\t")
            for ln in resp.toPlainText().splitlines()
            if ln.strip()
        ]
        entry = ExperienceEntry(
            title=title.text().strip(),
            company=company.text().strip(),
            location=location.text().strip(),
            start_date=start.text().strip(),
            end_date=end.text().strip(),
            responsibilities=responsibilities,
        )
        if not entry.title and not entry.company:
            return None
        return entry


class CertificateEditor(_EntryListEditor):
    def __init__(self, parent=None) -> None:
        super().__init__("Zertifikate / Weiterbildungen", parent)

    def create_item(self):
        return self._dialog()

    def edit_item(self, existing: CertificateEntry):
        return self._dialog(existing)

    def _dialog(self, existing: CertificateEntry | None = None) -> CertificateEntry | None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Zertifikat / Weiterbildung")
        name = QLineEdit(existing.name if existing else "")
        issuer = QLineEdit(existing.issuer if existing else "")
        date = QLineEdit(existing.date if existing else "")
        form = QFormLayout()
        form.addRow("Bezeichnung", name)
        form.addRow("Anbieter", issuer)
        form.addRow("Datum", date)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout = QVBoxLayout(dlg)
        layout.addLayout(form)
        layout.addWidget(buttons)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        if not name.text().strip():
            return None
        return CertificateEntry(
            name=name.text().strip(),
            issuer=issuer.text().strip(),
            date=date.text().strip(),
        )
