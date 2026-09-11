"""Structured pre-submit application preview (intended values / documents).

This is independent of the dry-run submit guard: preview shows what would be
sent; the guard still blocks the final click.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from apply.detector import ATSDetector, classify_ats_support
from core.config import AppConfig
from core.cover_letter import render_cover_letter
from core.models import Job


@dataclass
class ApplicationPreview:
    job_id: str
    company: str
    title: str
    application_url: str
    ats: str
    ats_support: str  # supported | unsupported | external_redirect | unknown
    ats_note: str
    dry_run: bool
    mode: str
    will_submit: bool
    match_score: int = 0
    form_values: dict[str, str] = field(default_factory=dict)
    documents: dict[str, str] = field(default_factory=dict)
    cover_letter_preview: str = ""
    screening_questions: dict[str, str] = field(default_factory=dict)
    intended_answers: dict[str, str] = field(default_factory=dict)
    unknown_fields: list[str] = field(default_factory=list)
    submit_allowed: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def text_report(self) -> str:
        lines = [
            f"Stelle: {self.title}",
            f"Firma: {self.company}",
            f"URL: {self.application_url or '—'}",
            f"ATS: {self.ats} ({self.ats_support})",
            f"Match: {self.match_score}%",
        ]
        if self.ats_note:
            lines.append(f"Hinweis: {self.ats_note}")
        lines.append(f"Modus: {self.mode} | Dry-Run: {'ja' if self.dry_run else 'nein'}")
        lines.append(
            f"Finales Absenden: {'JA' if self.submit_allowed and self.will_submit else 'NEIN (Guard aktiv)'}"
        )
        lines.append(f"submit_allowed: {self.submit_allowed}")
        lines.append("")
        lines.append("=== Geplante Formularwerte ===")
        for k, v in self.form_values.items():
            lines.append(f"• {k}: {v or '—'}")
        lines.append("")
        lines.append("=== Dokumente ===")
        for k, v in self.documents.items():
            lines.append(f"• {k}: {v or '—'}")
        if self.screening_questions or self.intended_answers:
            lines.append("")
            lines.append("=== Screening / Antworten ===")
            for k, v in self.intended_answers.items():
                lines.append(f"• {k}: {v or '—'}")
            for k, v in self.screening_questions.items():
                if k not in self.intended_answers:
                    lines.append(f"• {k}: {v or '—'}")
        if self.unknown_fields:
            lines.append("")
            lines.append("=== Unbekannte Felder ===")
            for u in self.unknown_fields:
                lines.append(f"• {u}")
        if self.cover_letter_preview:
            lines.append("")
            lines.append("=== Anschreiben (Vorschau) ===")
            lines.append(self.cover_letter_preview[:2000])
        if self.warnings:
            lines.append("")
            lines.append("=== Warnungen ===")
            for w in self.warnings:
                lines.append(f"• {w}")
        return "\n".join(lines)


def build_application_preview(job: Job, config: AppConfig) -> ApplicationPreview:
    """Build a human-readable preview of intended submit payload from profile + job."""
    app = config.application
    settings = config.settings
    url = job.application_url or job.url or ""
    ats = job.ats_type if job.ats_type and job.ats_type != "unknown" else ATSDetector.detect(url)
    if ats == "unknown":
        ats = ATSDetector.detect(url)
    support, note = classify_ats_support(ats, url)

    dry_run = bool(settings.dry_run)
    will_submit = (
        settings.mode == "fully_automatic"
        and not dry_run
        and bool(getattr(settings, "automatic_submission", False))
        and support == "supported"
    )

    cv_path = Path(app.cv_path) if app.cv_path else None
    if cv_path and not cv_path.is_absolute():
        cv_path = config.root / cv_path

    cover = ""
    try:
        cover = render_cover_letter(job, config)
    except Exception as exc:  # noqa: BLE001
        cover = f"(Anschreiben konnte nicht gerendert werden: {exc})"

    warnings: list[str] = []
    if support != "supported":
        warnings.append(
            "Automatisierung für dieses ATS ist nicht verfügbar — manuell öffnen/abschließen."
        )
    if dry_run:
        warnings.append("Dry-Run aktiv: finaler Submit-Klick ist blockiert.")
    if settings.mode == "fully_automatic" and not bool(getattr(settings, "automatic_submission", False)):
        warnings.append("Vollautomatik ohne automatische Abgabe: finaler Submit bleibt blockiert.")
    if not cv_path or not cv_path.exists():
        warnings.append("CV-Datei fehlt oder Pfad ungültig.")
    if not app.email or not app.first_name:
        warnings.append("Profil-Kontaktdaten unvollständig.")

    answers = dict(app.answers or {})
    submit_allowed = bool(will_submit) and not dry_run and support == "supported"

    return ApplicationPreview(
        job_id=job.id,
        company=job.company,
        title=job.title,
        application_url=url,
        ats=ats,
        ats_support=support,
        ats_note=note,
        dry_run=dry_run,
        mode=settings.mode,
        will_submit=will_submit,
        match_score=int(job.match_score or 0),
        form_values={
            "Vorname": app.first_name,
            "Nachname": app.last_name,
            "Geburtsdatum": app.date_of_birth,
            "E-Mail": app.email,
            "Telefon": app.phone_full or app.phone,
            "Straße": app.street,
            "PLZ": app.postal_code,
            "Ort": app.city,
            "Land": app.country,
            "Adresse": app.address or f"{app.street}, {app.postal_code} {app.city}".strip(", "),
            "LinkedIn": app.linkedin_url,
        },
        documents={
            "CV": str(cv_path) if cv_path else "",
            "Anschreiben": "(generiert, siehe unten)",
        },
        cover_letter_preview=cover,
        screening_questions={k: "" for k in answers},
        intended_answers=answers,
        unknown_fields=[],
        submit_allowed=submit_allowed,
        warnings=warnings,
    )
