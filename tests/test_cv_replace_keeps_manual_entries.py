"""Regression: UI-edited education/experience keep source=manual across CV replace."""

from __future__ import annotations

import inspect

from core.config import CertificateEntry, EducationEntry, ExperienceEntry, QualificationsConfig
from desktop.services.profile_merge import SOURCE_MANUAL, replace_qualifications
from desktop.widgets import structured_editors


def test_editors_assign_source_manual_in_dialog_code():
    """Ensure dialog construction paths set SOURCE_MANUAL (no Qt dialog needed)."""
    edu_src = inspect.getsource(structured_editors.EducationEditor._dialog)
    exp_src = inspect.getsource(structured_editors.ExperienceEditor._dialog)
    cert_src = inspect.getsource(structured_editors.CertificateEditor._dialog)
    assert "SOURCE_MANUAL" in edu_src
    assert "SOURCE_MANUAL" in exp_src
    assert "SOURCE_MANUAL" in cert_src
    # Empty legacy source must become manual when editing existing rows.
    assert "existing.source if existing" in edu_src


def test_replace_keeps_manual_education_and_experience():
    existing = QualificationsConfig(
        education=[
            EducationEntry(
                qualification="Selbst eingetragen",
                institution="Akademie",
                source=SOURCE_MANUAL,
            )
        ],
        work_experience=[
            ExperienceEntry(
                title="Buchhaltung",
                company="Firma GmbH",
                source=SOURCE_MANUAL,
            )
        ],
        certificates=[
            CertificateEntry(
                name="DATEV-Zertifikat",
                issuer="DATEV",
                source=SOURCE_MANUAL,
            )
        ],
    )
    incoming = QualificationsConfig(
        education=[
            EducationEntry(
                qualification="Aus CV",
                institution="Uni",
                source="cv",
            )
        ],
        work_experience=[
            ExperienceEntry(
                title="CV Job",
                company="CV Firma",
                source="cv",
            )
        ],
        certificates=[
            CertificateEntry(
                name="CV Zertifikat",
                issuer="IHK",
                source="cv",
            )
        ],
    )
    merged = replace_qualifications(existing, incoming)
    edu_quals = {e.qualification for e in merged.education}
    titles = {e.title for e in merged.work_experience}
    certs = {c.name for c in merged.certificates}
    assert "Selbst eingetragen" in edu_quals
    assert "Aus CV" in edu_quals
    assert "Buchhaltung" in titles
    assert "CV Job" in titles
    assert "DATEV-Zertifikat" in certs
    assert "CV Zertifikat" in certs
