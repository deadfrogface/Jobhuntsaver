"""Smoke tests for profile section load/save round-trips (no full GUI)."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from core.config import JobsConfig, QualificationsConfig, SourcedText
from desktop.pages.profile_sections import CareerSection, QualificationsSection


def _ensure_qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_career_section_round_trip():
    _ensure_qapp()
    section = CareerSection()
    jobs = JobsConfig(
        desired_titles=["Sachbearbeiter"],
        alternative_titles=["Assistent"],
        unwanted_titles=["Praktikant"],
        desired_industries=["Verwaltung"],
        excluded_industries=["Gastronomie"],
    )
    section.load(jobs)
    out = JobsConfig()
    section.save_into(out)
    assert out.desired_titles == ["Sachbearbeiter"]
    assert out.alternative_titles == ["Assistent"]
    assert out.unwanted_titles == ["Praktikant"]
    assert out.desired_industries == ["Verwaltung"]
    assert out.excluded_industries == ["Gastronomie"]


def test_qualifications_section_preserves_manual_skills():
    _ensure_qapp()
    section = QualificationsSection()
    quals = QualificationsConfig(
        skills=[SourcedText(value="Excel", source="manual")],
        software=[SourcedText(value="Outlook", source="cv")],
    )
    section.load(quals)
    section.save_into(quals)
    assert any(s.value == "Excel" for s in quals.skills)
