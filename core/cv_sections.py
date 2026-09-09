"""German CV section heading detection and body splitting."""

from __future__ import annotations

import re

HEADINGS = {
    "experience": (
        "berufserfahrung",
        "berufliche erfahrung",
        "beruflicher Werdegang",
        "experience",
        "work experience",
        "tätigkeiten",
        "beschäftigung",
        "karriere",
        "berufliche stationen",
    ),
    "education": (
        "ausbildung",
        "ausbildungen",
        "schulbildung",
        "schule",
        "studium",
        "education",
        "akademischer Werdegang",
        "schulischer Werdegang",
        "qualifikation",
        "qualifikationen",
    ),
    "certificates": (
        "weiterbildungen",
        "weiterbildung",
        "zertifikate",
        "zertifikat",
        "fortbildung",
        "fortbildungen",
        "licenses",
        "zertifizierung",
        "zertifizierungen",
        "kurse",
        "seminare",
    ),
    "languages": (
        "sprachen",
        "languages",
        "sprachkenntnisse",
        "fremdsprachen",
    ),
    "software": (
        "edv-kenntnisse",
        "edv kenntnisse",
        "edv",
        "it-kenntnisse",
        "it kenntnisse",
        "software",
        "kenntnisse",
        "it skills",
        "computerkenntnisse",
        "anwenderkenntnisse",
        "pc-kenntnisse",
        "pc kenntnisse",
    ),
    "license": (
        "führerschein",
        "fuehrerschein",
        "fahrerlaubnis",
        "driving licence",
        "driving license",
        "führerscheinklassen",
        "fuehrerscheinklassen",
    ),
    "skills": (
        "fähigkeiten",
        "kompetenzen",
        "skills",
        "stärken",
        "soft skills",
        "schlüsselkompetenzen",
        "fachkenntnisse",
    ),
    "profile": (
        "profil",
        "über mich",
        "ueber mich",
        "zusammenfassung",
        "summary",
        "persönliche daten",
        "persoenliche daten",
        "kontakt",
        "interessen",
        "hobbys",
        "hobby",
    ),
}

# Section heading tokens must never become field values.
ALL_HEADING_ALIASES = {
    alias.lower() for aliases in HEADINGS.values() for alias in aliases
}


def normalize_bullet(line: str) -> str:
    return re.sub(r"^[\s•\-–—*·]+", "", line).strip()


def is_heading(line: str) -> str | None:
    cleaned = line.strip().lower().rstrip(":")
    if not cleaned or len(cleaned) > 48:
        return None
    for key, aliases in HEADINGS.items():
        if cleaned in {a.lower() for a in aliases}:
            return key
    return None


def is_heading_value(text: str) -> bool:
    cleaned = text.strip().lower().rstrip(":")
    return cleaned in ALL_HEADING_ALIASES


def split_named_sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    sections: dict[str, list[str]] = {"general": []}
    current = "general"
    for raw in lines:
        line = raw.strip()
        if not line:
            sections.setdefault(current, []).append("")
            continue
        heading = is_heading(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        # Skip document title lines such as "Lebenslauf" / "Curriculum Vitae"
        if re.fullmatch(r"(tabellarischer\s+)?lebenslauf|curriculum\s+vitae", line, re.I):
            continue
        sections.setdefault(current, []).append(raw.rstrip())
    return {k: "\n".join(v).strip() for k, v in sections.items() if "".join(v).strip()}
