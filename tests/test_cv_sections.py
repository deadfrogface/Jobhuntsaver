"""CV section heading helper smoke tests."""

from core.cv_sections import is_heading, is_heading_value, split_named_sections


def test_is_heading_german_experience():
    assert is_heading("Berufserfahrung") == "experience"
    assert is_heading("Sprachen:") == "languages"
    assert is_heading("Not a heading at all because it is way too long for a section title") is None


def test_heading_values_are_rejected_as_field_content():
    assert is_heading_value("Führerschein") is True
    assert is_heading_value("B") is False


def test_split_named_sections_skips_lebenslauf_title():
    text = """Lebenslauf
Berufserfahrung
Sachbearbeiter bei Beispiel GmbH
Sprachen
Deutsch – C2
"""
    sections = split_named_sections(text)
    assert "experience" in sections
    assert "Sachbearbeiter" in sections["experience"]
    assert "languages" in sections
    assert "Deutsch" in sections["languages"]
