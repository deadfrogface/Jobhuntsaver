"""Focused CV parser guards for software substring + soft-skill false positives.

Fictional strings only — no real PII.
"""

from __future__ import annotations

from core.cv_parser import (
    _looks_like_soft_skill,
    _looks_like_software,
    parse_cv_text,
)


def test_software_tokens_require_word_boundary() -> None:
    # Substring traps that previously matched "word" / "sap" / "java".
    assert not _looks_like_software("Teamwork")
    assert not _looks_like_software("Password Manager")
    assert not _looks_like_software("WhatsApp Business")
    assert not _looks_like_software("Javascript Notes")
    assert _looks_like_software("MS Word")
    assert _looks_like_software("SAP")
    assert _looks_like_software("Java")


def test_bare_management_and_tion_not_soft_skill_overmatch() -> None:
    assert not _looks_like_soft_skill("Management")
    assert not _looks_like_soft_skill("Process Automation")
    assert not _looks_like_soft_skill("Technical Documentation")
    # Real soft-skill compounds / phrases still count.
    assert _looks_like_soft_skill("Beschwerdemanagement")
    assert _looks_like_soft_skill("Kundenorientierung")
    assert _looks_like_soft_skill("Change Management")
    assert _looks_like_soft_skill("Hohe Belastbarkeit")


def test_soft_skills_relocated_even_when_skills_nonempty() -> None:
    text = """
Alex Beispiel
Skills
Kommunikation

EDV-Kenntnisse
Excel
Beschwerdemanagement
Kundenorientierung
"""
    parsed = parse_cv_text(text)
    soft = " | ".join(s.lower() for s in parsed["software"])
    skills = " | ".join(s.lower() for s in parsed["skills"])
    assert "excel" in soft
    assert "beschwerdemanagement" not in soft
    assert "kundenorientierung" not in soft
    assert "kommunikation" in skills
    assert "beschwerdemanagement" in skills
    assert "kundenorientierung" in skills
