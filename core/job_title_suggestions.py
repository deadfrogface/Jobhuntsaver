"""Derive job-title suggestions from parsed CV / qualifications.

Suggestions are profile-dependent and never invent careers that require
credentials clearly absent from the profile. Manual user titles are preserved
by the caller — this module only proposes candidates.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# Map experience/education tokens → suggested search titles (DE + EN variants).
_TOKEN_TITLES: list[tuple[re.Pattern[str], list[str]]] = [
    (
        re.compile(r"kundenberat|customer\s*service|customer\s*support|verkaufsberat|sales\s*advisor", re.I),
        ["Kundenberater", "Verkaufsberater", "Customer Service", "Customer Support"],
    ),
    (
        re.compile(r"sachbearbeit|backoffice|rechnungsmanagement|rechnungswesen|buchhalt|datev|rechnungspr|accounting|accounts\s*payable", re.I),
        ["Sachbearbeiter", "Backoffice", "kaufmännischer Mitarbeiter", "Rechnungsprüfer"],
    ),
    (
        re.compile(r"office\s*management|büromanagement|office\s*manager|verwaltung|administrative", re.I),
        ["Office Manager", "Office Management", "Assistent", "Verwaltungsmitarbeiter"],
    ),
    (
        re.compile(r"vertriebsinnendienst|inside\s*sales|innendienst", re.I),
        ["Vertriebsinnendienst", "Inside Sales", "Kundenberater"],
    ),
    (
        re.compile(r"on[- ]?site\s*support|it[- ]?support|helpdesk|first\s*level", re.I),
        ["IT-Support", "On-Site Support", "Helpdesk"],
    ),
    (
        re.compile(r"barkeeper|servicekraft|gastronom|hotel", re.I),
        ["Servicekraft", "Gastronomie", "Hotelfachkraft"],
    ),
    (
        re.compile(r"fitness|trainer|zumba|pilates|ems", re.I),
        ["Fitnesstrainer", "Sport- und Fitnesskaufmann"],
    ),
    (
        re.compile(r"zeitarbeit|personaldisponent|staffing", re.I),
        ["Sachbearbeiter", "Personalsachbearbeiter"],
    ),
]

_EXCLUDE_DEFAULT = ["Werkstudent", "Praktikant", "Trainee"]


def _texts_from_parsed(parsed: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for line in parsed.get("experience_lines") or []:
        out.append(str(line))
    for exp in (parsed.get("work_experience") or parsed.get("experience") or []):
        if isinstance(exp, dict):
            out.extend(
                str(exp.get(k) or "")
                for k in ("title", "company", "description", "responsibilities")
            )
            resp = exp.get("responsibilities")
            if isinstance(resp, list):
                out.extend(str(x) for x in resp)
        else:
            out.append(str(exp))
    for edu in (parsed.get("education") or []):
        if isinstance(edu, dict):
            out.extend(str(edu.get(k) or "") for k in ("degree", "field", "school", "title"))
        else:
            out.append(str(edu))
    for key in ("skills", "software", "certificates"):
        for item in parsed.get(key) or []:
            if isinstance(item, dict):
                out.append(str(item.get("name") or item.get("value") or ""))
            else:
                out.append(str(item))
    return [t for t in out if t and t.strip()]


def suggest_job_titles(
    parsed: dict[str, Any] | None = None,
    *,
    existing_desired: Iterable[str] | None = None,
    existing_alternative: Iterable[str] | None = None,
    limit: int = 8,
) -> dict[str, list[str]]:
    """Return ``desired`` / ``alternative`` suggestion lists (deduped).

    Existing user choices are excluded from the suggestion lists so the UI can
    merge without overwriting.
    """
    blob = "\n".join(_texts_from_parsed(parsed or {}))
    existing = {
        re.sub(r"\s+", " ", t.strip().lower())
        for t in list(existing_desired or []) + list(existing_alternative or [])
        if t and str(t).strip()
    }

    desired: list[str] = []
    alternative: list[str] = []
    for pattern, titles in _TOKEN_TITLES:
        if not blob or not pattern.search(blob):
            continue
        for i, title in enumerate(titles):
            key = title.lower()
            if key in existing:
                continue
            if i == 0:
                if title not in desired:
                    desired.append(title)
            else:
                if title not in desired and title not in alternative:
                    alternative.append(title)

    # Also promote clear prior job titles from experience when short enough.
    for exp in ((parsed or {}).get("work_experience") or (parsed or {}).get("experience") or []):
        title = ""
        if isinstance(exp, dict):
            title = str(exp.get("title") or "").strip()
        if not title or len(title) > 60:
            continue
        key = title.lower()
        if key in existing or title in desired or title in alternative:
            continue
        if any(x in key for x in ("werkstudent", "praktik", "trainee", "minijob")):
            continue
        if len(desired) < max(3, limit // 2):
            desired.append(title)
        else:
            alternative.append(title)

    return {
        "desired": desired[:limit],
        "alternative": alternative[:limit],
        "exclusions_suggested": list(_EXCLUDE_DEFAULT),
    }
