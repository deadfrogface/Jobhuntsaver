"""Pre-submit application preview dialog with READY/WARNING/BLOCKED gate."""

from __future__ import annotations

import webbrowser

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from apply.preview import ApplicationPreview
from desktop.i18n import tr


class ApplyPreviewDialog(QDialog):
    """Show intended form values / documents before any real submit."""

    def __init__(self, preview: ApplicationPreview, parent=None) -> None:
        super().__init__(parent)
        self.preview = preview
        self.setWindowTitle(tr("apps.preview_title"))
        self.resize(720, 560)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.gate = QLabel()
        self.gate.setWordWrap(True)
        self.body = QPlainTextEdit()
        self.body.setReadOnly(True)
        self.body.setPlainText(preview.text_report())

        self.open_url_btn = QPushButton(tr("btn.open_manual"))
        self.open_url_btn.clicked.connect(self._open_url)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn:
            close_btn.setText(tr("btn.close") if tr("btn.close") != "btn.close" else "Schließen")

        top = QHBoxLayout()
        top.addWidget(self.summary, 1)
        top.addWidget(self.open_url_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.gate)
        layout.addWidget(self.body, 1)
        layout.addWidget(buttons)

        submit_note = (
            tr("apps.preview_will_submit")
            if preview.will_submit
            else tr("apps.preview_no_submit")
        )
        if submit_note.startswith("apps."):
            submit_note = (
                "Finales Absenden wäre erlaubt."
                if preview.will_submit
                else "Finales Absenden ist blockiert (Dry-Run / Review)."
            )
        title = tr("apps.preview_title")
        if title.startswith("apps."):
            title = "Bewerbungsvorschau (vor Absenden)"
        self.setWindowTitle(title)
        company = preview.company or "—"
        doc = ""
        if preview.document_filename or preview.document_role:
            doc = (
                f"<br/>Dokument: <b>{preview.document_role or 'cv'}</b> — "
                f"{preview.document_filename or '—'}"
            )
        self.summary.setText(
            f"<b>{company}</b> — {preview.title}<br/>"
            f"ATS: {preview.ats} ({preview.ats_support})<br/>{submit_note}{doc}"
        )
        gate = getattr(preview, "quality_gate", "WARNING") or "WARNING"
        gate_key = {
            "READY": tr("apps.gate_ready"),
            "WARNING": tr("apps.gate_warning"),
            "BLOCKED": tr("apps.gate_blocked"),
        }.get(gate, gate)
        if str(gate_key).startswith("apps."):
            gate_key = {
                "READY": "Qualität: READY — bereit zur Vorbereitung",
                "WARNING": "Qualität: WARNING — bitte prüfen",
                "BLOCKED": "Qualität: BLOCKED — CV/Profil blockiert",
            }.get(gate, gate)
        color = {"READY": "#1b7f3a", "WARNING": "#9a6b00", "BLOCKED": "#a11"}.get(gate, "#333")
        self.gate.setText(f"<span style='color:{color}; font-weight:600'>{gate_key}</span>")

    def _open_url(self) -> None:
        url = self.preview.application_url
        if url:
            webbrowser.open(url)
