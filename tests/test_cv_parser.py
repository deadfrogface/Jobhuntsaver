"""CV parser tests — must not invent qualifications."""

from core.cv_parser import parse_cv_text


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
    # Must not invent a degree that isn't there
    assert not any("Master" in e for e in parsed["education"])


def test_empty_cv():
    assert parse_cv_text("")["skills"] == []
