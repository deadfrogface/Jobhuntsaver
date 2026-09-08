"""CV parser tests — must not invent qualifications."""

from pathlib import Path

import pytest

from core.config import parse_qualifications, strip_example_placeholders, ProfileConfig, QualificationsConfig, LanguageEntry
from core.cv_parser import import_cv, parse_cv_text, parsed_to_qualifications
from desktop.services.profile_merge import merge_qualifications


def test_parse_cv_extracts_only_present_data():
    text = """
Max Mustermann
max@example.com
+49 170 1234567

Skills
Excel, Outlook, SAP

Languages
Deutsch C1
Englisch B1

Experience
Kundenberater bei Firma X
"""
    parsed = parse_cv_text(text)
    assert "max@example.com" in parsed["emails"]
    assert any("Excel" in s for s in parsed["skills"])
    assert not any("Master" in str(e) for e in parsed["education"])


def test_empty_cv():
    assert parse_cv_text("")["skills"] == []


def test_structured_german_cv_sections():
    text = """
Berufserfahrung
Seit 28.08.2025
Disponentin
Nordhafen Logistik GmbH
• Verkaufsberatung sowie Betreuung
• Beschwerdemanagement und professionelle Reklamationsbearbeitung
• Ganzheitliche Betreuung von B2C- und B2B-Kunden

01.02.2024 – 25.07.2025
Sachbearbeiterin Versand
Seeland Versand KG, Lübeck
• Bearbeitung von Rechnungen

Ausbildung
Berufsausbildung – Kauffrau für Spedition und Logistikdienstleistung
Abschluss: 06.07.2023
Nordhafen Logistik GmbH, Hamburg
Seeland Ausbildungszentrum, Lübeck
Mittlere Reife
Abschluss: 23.07.2020
Stadtteilschule Alsterblick

Weiterbildungen
• Zollgrundlagen
• Staplerschein
• Ersthelfer
• Lagerfachkraft Basis

Sprachen
• Deutsch (Muttersprache) – C2
• Englisch – C1
• Dänisch – A2

EDV-Kenntnisse
• MS Office (Word, Excel – fortgeschritten)
• Shopify
• Power BI, Microsoft Teams
• SAP S/4HANA
• Individuell entwickeltes Versandverwaltungssystem (Versand Office)
• Interne Backoffice-Systeme (Nordhafen Backoffice)

Führerschein
• Klasse B (PKW)
"""
    q = parsed_to_qualifications(parse_cv_text(text))
    langs = {(l.language, l.level) for l in q.languages}
    assert ("Deutsch", "C2") in langs
    assert ("Englisch", "C1") in langs
    assert ("Dänisch", "A2") in langs
    assert ("Schwedisch", "A2") in langs
    assert any("Klasse B" in d for d in q.driving_license)
    assert any("Kauffrau für Spedition und Logistikdienstleistung" in e.qualification for e in q.education)
    assert any("Mittlere Reife" in e.qualification for e in q.education)
    assert any("06.07.2023" == e.completion_date for e in q.education)
    assert any("Zollgrundlagen" == c.name for c in q.certificates)
    assert any("Shopify" == s for s in q.software)
    assert any("Excel" in s for s in q.software)
    assert len(q.work_experience) >= 2
    assert any("Reklamationsbearbeitung" in " ".join(e.responsibilities) for e in q.work_experience)


def test_real_test_cv_if_present():
    path = Path(r"tests/fixtures/cv_structured_de.txt")
    if not path.exists():
        pytest.skip("Test CV PDF not present on this machine")
    q = parsed_to_qualifications(import_cv(path))
    assert len(q.languages) >= 4
    assert any(l.language == "Englisch" and l.level == "C1" for l in q.languages)
    assert any("Klasse B" in d for d in q.driving_license)
    assert any("Speditionskauffrau" in e.qualification for e in q.education)
    assert any(c.name == "Zollgrundlagen" for c in q.certificates)
    assert len(q.work_experience) >= 3


def test_example_placeholders_stripped():
    profile = ProfileConfig(
        qualifications=QualificationsConfig(
            skills=["MS Office", "Kommunikation"],
            software=["Excel", "Outlook"],
            languages=[
                LanguageEntry(language="Deutsch", level="C1"),
                LanguageEntry(language="Englisch", level="B1"),
            ],
        )
    )
    cleaned = strip_example_placeholders(profile)
    assert cleaned.qualifications.skills == []
    assert cleaned.qualifications.software == []
    assert cleaned.qualifications.languages == []


def test_reimport_no_duplicates():
    existing = QualificationsConfig(
        languages=[LanguageEntry(language="Deutsch", level="C1")],
        software=["Excel"],
        certificates=[],
    )
    incoming = QualificationsConfig(
        languages=[
            LanguageEntry(language="Deutsch", level="C2"),
            LanguageEntry(language="Englisch", level="C1"),
        ],
        software=["Excel", "Shopify"],
    )
    merged_add = merge_qualifications(existing, incoming, languages="add", software="add")
    assert len(merged_add.languages) == 2  # Deutsch kept once, Englisch added
    assert {l.language for l in merged_add.languages} == {"Deutsch", "Englisch"}
    assert merged_add.software == ["Excel", "Shopify"]

    merged_update = merge_qualifications(
        existing, incoming, languages="update", software="update"
    )
    deutsch = next(l for l in merged_update.languages if l.language == "Deutsch")
    assert deutsch.level == "C2"
