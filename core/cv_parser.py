"""Structured German/English CV profile parsing.

Text extraction: ``core.cv_extract``. Section headings/split: ``core.cv_sections``.
This module never invents qualifications that are not present in the text. No paid AI.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from core.config import (
    CertificateEntry,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
    QualificationsConfig,
    parse_qualifications,
)
from core.cv_extract import extract_text
from core.cv_sections import (
    is_document_title as _is_document_title,
    is_heading as _is_heading,
    is_heading_value as _is_heading_value,
    normalize_bullet as _normalize_bullet,
    split_named_sections as _split_named_sections,
)

logger = logging.getLogger("jobhuntsaver")

_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
_DATE = (
    rf"(?:{_MONTH}\s+\d{{4}}|"
    r"\d{1,2}\.\d{1,2}\.\d{2,4}|"
    r"\d{1,2}[./]\d{4}|"
    r"\d{4})"
)
_END = rf"(?:{_DATE}|heute|aktuell|present|current)"
_PERIOD = re.compile(
    rf"(?P<start>(?:Seit|seit)\s+{_DATE}|{_DATE})\s*[–\-—]\s*(?P<end>{_END})",
    re.IGNORECASE,
)
_SINCE = re.compile(rf"^(?:Seit|seit)\s+(?P<start>{_DATE})\s*$", re.IGNORECASE)
_SINCE_INLINE = re.compile(
    rf"^(?:Seit|seit)\s+(?P<start>{_DATE})\s*[–\-—]?\s+(?P<title>.+)$",
    re.IGNORECASE,
)
_ABSCHLUSS = re.compile(
    rf"Abschluss\s*:\s*(?P<date>{_DATE})",
    re.IGNORECASE,
)
_LEVEL = re.compile(
    r"\b([ABC][12]|Muttersprache|Muttersprachler(?:in)?|native(?:\s+speaker)?)\b",
    re.IGNORECASE,
)

# EU driving licence class tokens (normalized uppercase).
# Order matters for alternation: longer tokens first so BE matches before B, C1E before C1, etc.
_LICENSE_CLASS = re.compile(
    r"\b(AM|A1|A2|A|B1|BE|B|C1E|C1|CE|C|D1E|D1|DE|D|L|T)\b",
    re.IGNORECASE,
)

_DEGREE_HINT = re.compile(
    r"(?i)\b("
    r"bachelor|master|b\.?a\.?|b\.?sc\.?|bcom|m\.?a\.?|m\.?sc\.?|mba|"
    r"ausbildung|kaufmann|kauffrau|abitur|fachabitur|realschule|"
    r"hauptschule|mittlere\s+reife|fachhochschulreife|studium|"
    r"promotion|diplom|ihk|university|hochschule|college|a\s*levels?"
    r")\b"
)


def normalize_driving_license(raw: str | list[str]) -> list[str]:
    """Normalize German/EU licence text to class codes like ``B``, ``BE``, ``C1``."""
    chunks = raw if isinstance(raw, list) else [raw]
    found: list[str] = []
    for chunk in chunks:
        text = str(chunk or "").strip()
        if not text or _is_heading_value(text):
            continue
        for m in _LICENSE_CLASS.finditer(text):
            code = m.group(1).upper()
            if code not in found:
                found.append(code)
    return found


def field_confidence(value: Any) -> str:
    """Return ``high`` / ``low`` / ``Nicht erkannt`` for empty values."""
    if value is None:
        return "Nicht erkannt"
    if isinstance(value, (list, dict, str)) and not value:
        return "Nicht erkannt"
    if isinstance(value, list) and all(not str(v).strip() for v in value):
        return "Nicht erkannt"
    return "high"


def _split_language_chunks(line: str) -> list[str]:
    """Split one line that may contain several language/level pairs."""
    # "English - Native | German - B2 | French - A2"
    # "Deutsch: Muttersprache; Englisch: B2"
    # Do NOT split "Deutsch | C2" (single pair).
    cefr_hits = len(re.findall(r"\b(?:[ABC][12]|Muttersprache|Muttersprachler(?:in)?|native)\b", line, re.I))
    seps = len(re.findall(r"[|;]", line))
    if seps >= 1 and cefr_hits >= 2:
        return [p.strip() for p in re.split(r"\s*[|;]\s*", line) if p.strip()]
    if re.search(r",\s*[A-Za-zÄÖÜäöüß].*(?:[ABC][12]|Muttersprache|native)", line, re.I):
        # "Deutsch C2, Englisch B2, Tschechisch A2"
        if cefr_hits >= 2:
            return [p.strip() for p in re.split(r"\s*,\s*", line) if p.strip()]
    return [line]


def _normalize_lang_level(level: str, meta: str = "", full_line: str = "") -> str:
    level = (level or "").strip()
    meta = (meta or "").strip()
    blob = f"{meta} {level} {full_line}"
    # Prefer explicit CEFR anywhere on the line over Muttersprache/native wording.
    cefr = re.findall(r"\b([ABC][12])\b", blob, re.I)
    if cefr:
        return cefr[-1].upper()
    low = blob.lower()
    if "muttersprach" in low or re.search(r"\bnative(?:\s+speaker)?\b", low):
        return "native"
    if re.fullmatch(r"[ABC][12]", level, re.I):
        return level.upper()
    return level


def _parse_one_language(chunk: str) -> LanguageEntry | None:
    line = chunk.strip().strip("•-–—*· ")
    if not line or _is_heading_value(line):
        return None

    m = re.match(
        r"^(?P<lang>[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-/']*)\s*"
        r"(?:[–\-—|:]\s*)?(?P<body>.+)?$",
        line,
        re.I,
    )
    if m:
        lang = m.group("lang").strip(" :")
        body = (m.group("body") or "").strip()
        if lang and not _is_heading_value(lang):
            level = _normalize_lang_level(body, full_line=line)
            if level or body:
                return LanguageEntry(language=lang, level=level)
    level_m = _LEVEL.search(line)
    if level_m:
        lang = line[: level_m.start()].strip(" -–—|():")
        if lang and not _is_heading_value(lang):
            return LanguageEntry(
                language=lang,
                level=_normalize_lang_level(level_m.group(1), full_line=line),
            )
    return None


def _parse_languages(body: str) -> list[LanguageEntry]:
    results: list[LanguageEntry] = []
    for raw in body.splitlines():
        line = _normalize_bullet(raw)
        if not line:
            continue
        for chunk in _split_language_chunks(line):
            amp = re.match(
                r"^(?P<langs>.+?)\s*[–\-—|:]\s*(?P<level>[ABC][12]|Muttersprache|native(?:\s+speaker)?)\s*$",
                chunk,
                re.I,
            )
            if amp and ("&" in amp.group("langs") or " und " in amp.group("langs").lower()):
                level = _normalize_lang_level(amp.group("level"), full_line=chunk)
                parts = re.split(r"\s*(?:&| und )\s*", amp.group("langs"), flags=re.I)
                for part in parts:
                    name = re.sub(r"\(.*?\)", "", part).strip(" -–—|:")
                    if name and not _is_heading_value(name):
                        results.append(LanguageEntry(language=name, level=level))
                continue
            entry = _parse_one_language(chunk)
            if entry:
                results.append(entry)
    seen: set[str] = set()
    unique: list[LanguageEntry] = []
    for item in results:
        key = item.normalized_key()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _parse_software(body: str) -> list[str]:
    items: list[str] = []
    for raw in body.splitlines():
        line = _normalize_bullet(raw)
        if not line or _is_heading_value(line):
            continue
        # Skip licence / mobility fragments accidentally mixed in.
        if re.match(r"(?i)^(führerschein|fuehrerschein|driving\s+licen)", line):
            continue
        m = re.match(r"^(?P<head>MS Office)\s*\((?P<inner>.+)\)$", line, re.I)
        if m:
            items.append(m.group("head"))
            inner = m.group("inner")
            chunks = re.split(r",|/", inner)
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                if "excel" in chunk.lower():
                    items.append(
                        "Excel – fortgeschritten"
                        if "fortgeschritten" in chunk.lower() or "fortgeschritten" in inner.lower()
                        else "Excel"
                    )
                elif "word" in chunk.lower():
                    items.append("Word")
                else:
                    items.append(chunk)
            continue
        # Split on comma/pipe only — keep versioned product names like SAP S/4HANA.
        if re.search(r"[,|]", line) and not re.search(r"\(.+[,|].+\)", line):
            for part in re.split(r"[,|]", line):
                part = part.strip()
                if part and not _is_heading_value(part):
                    items.append(part)
            continue
        paren = re.match(r"^(?P<desc>.+?)\s*\((?P<name>[^)]+)\)\s*$", line)
        if paren and len(paren.group("name")) < 40:
            items.append(f"{paren.group('name').strip()} / {paren.group('desc').strip()}")
            items.append(paren.group("name").strip())
            continue
        items.append(line)
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        if item.lower() == "excel" and any(
            "excel" in c.lower() and "fortgeschritten" in c.lower() for c in items
        ):
            continue
        seen.add(key)
        cleaned.append(item)
    return cleaned


def _parse_certificates(body: str) -> list[CertificateEntry]:
    result: list[CertificateEntry] = []
    for raw in body.splitlines():
        line = _normalize_bullet(raw)
        if not line or _is_heading_value(line):
            continue
        # Strip trailing years: "IHK Beschwerdemanagement, 2024"
        line = re.sub(r",?\s*\b(?:19|20)\d{2}\b\s*$", "", line).strip(" ,;")
        parts = re.split(r"\s*;\s*", line) if ";" in line else [line]
        for part in parts:
            part = part.strip()
            if part and not _is_heading_value(part):
                result.append(CertificateEntry(name=part))
    return result


def _parse_driving(body: str) -> list[str]:
    lines = [_normalize_bullet(raw) for raw in body.splitlines() if _normalize_bullet(raw)]
    normalized = normalize_driving_license(lines)
    if normalized:
        return normalized
    result: list[str] = []
    for line in lines:
        if _is_heading_value(line):
            continue
        low = line.lower()
        if "führerschein" in low or "fuehrerschein" in low or "fahrerlaubnis" in low:
            continue
        if "driving" in low and "licen" in low:
            continue
        result.append(line)
    return list(dict.fromkeys(result))


def _inline_licence_mentions(text: str) -> list[str]:
    """Only extract licences from explicit licence phrases — never bare CEFR tokens."""
    found: list[str] = []
    patterns = (
        r"(?:Führerschein|Fuehrerschein|Fahrerlaubnis|Driving\s+Licen[cs]e)\s*[:\-]\s*([^\n|;]+)",
        r"Klassen?\s+([A-Z0-9]{1,3}(?:\s*(?:und|,|/|&)\s*[A-Z0-9]{1,3})*)",
        r"Category\s+([A-Z0-9]{1,3})",
        r"Klasse\s+([A-Z0-9]{1,3})",
    )
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            found.extend(normalize_driving_license(m.group(1)))
    return list(dict.fromkeys(found))


_QUAL_START = re.compile(
    r"^(Berufsausbildung|Ausbildung\s+zum|Ausbildung\s+zur|"
    r"Kaufmann|Kauffrau|Mittlere Reife|Fachhochschulreife|Abitur|Bachelor|Master|"
    r"Studium|Fachabitur|Realschulabschluss|Hauptschulabschluss|Promotion|"
    r"B\.?\s*A\.?|B\.?\s*Sc\.?|BCom|M\.?\s*A\.?|M\.?\s*Sc\.?|MBA|A\s*Levels?)",
    re.IGNORECASE,
)


def _looks_like_certificate_line(line: str) -> bool:
    """Single-year training/cert line without a degree-range."""
    if _PERIOD.search(line):
        return False
    if _DEGREE_HINT.search(line) and re.search(r"\d{4}\s*[–\-—]\s*\d{4}", line):
        return False
    return bool(re.match(r"^(?:19|20)\d{2}\s+\S+", line))


def _parse_education(body: str) -> tuple[list[EducationEntry], list[CertificateEntry]]:
    lines = [ln.rstrip() for ln in body.splitlines()]
    entries: list[EducationEntry] = []
    leftover_certs: list[CertificateEntry] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith(("•", "-", "–")):
            i += 1
            continue
        if line.lower().startswith("abschluss"):
            i += 1
            continue
        if _is_heading(line):
            i += 1
            continue

        # Date-first layouts: "2013 - 2016 BA Business ..., University"
        pm = _PERIOD.search(line)
        if pm and (pm.start() < 3 or line.lower().startswith("seit")):
            rest = line[pm.end() :].strip(" |–—-")
            start = pm.group("start").replace("Seit ", "").replace("seit ", "").strip()
            end = pm.group("end").strip()
            qualification = rest
            institution = ""
            location = ""
            j = i + 1
            # Continuation lines for institution
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt:
                    j += 1
                    continue
                if _PERIOD.search(nxt) or _QUAL_START.match(nxt) or _is_heading(nxt) or _looks_like_certificate_line(nxt):
                    break
                if not qualification:
                    qualification = nxt
                elif not institution:
                    institution = nxt
                else:
                    institution = f"{institution} {nxt}".strip()
                j += 1
            if qualification and "|" in qualification:
                left, right = [p.strip() for p in qualification.split("|", 1)]
                qualification, institution = left, right or institution
            if qualification and "," in qualification and not institution:
                # "BA Business Management, University of the West of England"
                left, right = qualification.split(",", 1)
                if _DEGREE_HINT.search(left) or len(left.split()) <= 8:
                    qualification, institution = left.strip(), right.strip()
            if qualification:
                # Pipe leftovers: "Kaufmann ... (IHK) | Nordwest ... | Note 2,1"
                chunks = [c.strip() for c in qualification.split("|") if c.strip()]
                if len(chunks) >= 2 and not institution:
                    qualification = chunks[0]
                    institution = " / ".join(chunks[1:])
                    note_m = re.search(r"Note\s+[\d,]+", institution, re.I)
                    if note_m:
                        institution = institution[: note_m.start()].strip(" |/")
                entries.append(
                    EducationEntry(
                        qualification=qualification,
                        institution=institution,
                        location=location,
                        start_date=start,
                        end_date=end,
                        completion_date=end if re.search(r"\d", end) else "",
                    )
                )
            i = max(j, i + 1)
            continue

        # Single-year certificate-like lines inside education & training
        if _looks_like_certificate_line(line):
            name = re.sub(r"^(?:19|20)\d{2}\s+", "", line).strip()
            if name:
                leftover_certs.append(CertificateEntry(name=name))
            i += 1
            continue

        if not _QUAL_START.match(line):
            i += 1
            continue
        qualification = line
        completion = ""
        institution_parts: list[str] = []
        locations: list[str] = []
        j = i + 1
        while j < len(lines):
            nxt = lines[j].strip()
            if not nxt:
                j += 1
                continue
            if _is_heading(nxt) or _QUAL_START.match(nxt) or _PERIOD.search(nxt):
                break
            am = _ABSCHLUSS.search(nxt)
            if am:
                completion = am.group("date")
                j += 1
                continue
            if nxt.startswith(("•", "-", "–")):
                j += 1
                continue
            if "," in nxt:
                left, right = nxt.rsplit(",", 1)
                institution_parts.append(left.strip())
                if right.strip():
                    locations.append(right.strip())
            else:
                institution_parts.append(nxt)
            j += 1
        entries.append(
            EducationEntry(
                qualification=qualification,
                institution=" / ".join(institution_parts) if institution_parts else "",
                location=", ".join(dict.fromkeys(locations)),
                completion_date=completion,
                end_date=completion,
            )
        )
        i = max(j, i + 1)
    return [e for e in entries if e.qualification], leftover_certs


def _parse_experience(body: str) -> list[ExperienceEntry]:
    lines = [ln.rstrip() for ln in body.splitlines()]
    entries: list[ExperienceEntry] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if _is_heading(line):
            i += 1
            continue

        start = end = ""
        title = ""
        company = ""
        location = ""

        sm_inline = _SINCE_INLINE.match(line)
        pm = _PERIOD.search(line)
        sm = _SINCE.match(line)

        if sm_inline and not pm:
            start = sm_inline.group("start")
            end = "aktuell"
            title = sm_inline.group("title").strip(" |–—-")
            i += 1
        elif pm and pm.start() <= 2:
            start = pm.group("start").replace("Seit ", "").replace("seit ", "").strip()
            end = pm.group("end").strip()
            rest = line[pm.end() :].strip(" |–—-")
            i += 1
            if rest:
                # "date | title | company" or "date - title"
                parts = [p.strip() for p in re.split(r"\s*\|\s*", rest) if p.strip()]
                if len(parts) >= 2:
                    title = parts[0]
                    company = parts[1]
                    if len(parts) >= 3:
                        location = parts[2]
                else:
                    title = rest
        elif sm:
            start = sm.group("start")
            end = "aktuell"
            i += 1
        else:
            if line.startswith(("•", "-", "–", "*")):
                i += 1
                continue
            # Title-/company-first layouts: peek ahead for a date line.
            look = None
            look_idx = None
            for j in range(i + 1, min(i + 4, len(lines))):
                cand = lines[j].strip()
                if not cand:
                    continue
                if (
                    _PERIOD.search(cand)
                    or _SINCE.match(cand)
                    or _SINCE_INLINE.match(cand)
                ):
                    look = cand
                    look_idx = j
                    break
                if _is_heading(cand) or cand.startswith(("•", "-", "–", "*")):
                    break
            if look is None or look_idx is None:
                i += 1
                continue
            title = line
            # Optional company line between title and date
            company_candidate = ""
            for j in range(i + 1, look_idx):
                mid = lines[j].strip()
                if mid and not mid.startswith(("•", "-", "–", "*")):
                    company_candidate = mid
                    break
            if company_candidate:
                company = company_candidate
            sm_inline = _SINCE_INLINE.match(look)
            pm = _PERIOD.search(look)
            sm = _SINCE.match(look)
            if sm_inline and not pm:
                start = sm_inline.group("start")
                end = "aktuell"
                if sm_inline.group("title").strip():
                    # rare: "Seit DATE title" after company
                    pass
            elif pm:
                start = pm.group("start").replace("Seit ", "").replace("seit ", "").strip()
                end = pm.group("end").strip()
            elif sm:
                start = sm.group("start")
                end = "aktuell"
            i = look_idx + 1

        def _next_nonempty(idx: int) -> tuple[int, str]:
            while idx < len(lines) and not lines[idx].strip():
                idx += 1
            if idx >= len(lines):
                return idx, ""
            return idx, lines[idx].strip()

        if not title:
            i, title = _next_nonempty(i)
            if title and not (_PERIOD.search(title) or _SINCE.match(title) or _is_heading(title)):
                i += 1
            else:
                title = ""

        # Title may still contain "title | company"
        if title and "|" in title and not company:
            parts = [p.strip() for p in title.split("|")]
            title = parts[0]
            if len(parts) > 1:
                company = parts[1]
            if len(parts) > 2:
                location = parts[2]

        if not company:
            i, company_line = _next_nonempty(i)
            if company_line and not (
                _PERIOD.search(company_line)
                or _SINCE.match(company_line)
                or _is_heading(company_line)
                or company_line.startswith(("•", "-", "–", "*"))
            ):
                company = company_line
                i += 1
                if "," in company_line:
                    company, location = [p.strip() for p in company_line.rsplit(",", 1)]

        responsibilities: list[str] = []
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt:
                i += 1
                if i < len(lines) and (
                    _PERIOD.search(lines[i].strip()) or _SINCE.match(lines[i].strip()) or _SINCE_INLINE.match(lines[i].strip())
                ):
                    break
                continue
            if _PERIOD.search(nxt) or _SINCE.match(nxt) or _SINCE_INLINE.match(nxt) or _is_heading(nxt):
                break
            # Next job starting as title/company before its date — leave for outer loop.
            if not nxt.startswith(("•", "-", "–", "*")):
                upcoming_date = False
                for j in range(i + 1, min(i + 4, len(lines))):
                    cand = lines[j].strip()
                    if not cand:
                        continue
                    if _PERIOD.search(cand) or _SINCE.match(cand) or _SINCE_INLINE.match(cand):
                        upcoming_date = True
                        break
                    if cand.startswith(("•", "-", "–", "*")) or _is_heading(cand):
                        break
                if upcoming_date:
                    break
            cleaned = _normalize_bullet(nxt)
            if cleaned:
                responsibilities.append(cleaned)
            i += 1

        if title or company:
            entries.append(
                ExperienceEntry(
                    title=title,
                    company=company,
                    location=location,
                    start_date=start,
                    end_date=end,
                    responsibilities=responsibilities,
                )
            )
    return entries


def _parse_skills(body: str) -> list[str]:
    skills: list[str] = []
    for raw in body.splitlines():
        line = _normalize_bullet(raw)
        if not line or _is_heading_value(line) or _is_heading(line):
            continue
        # PDF extraction sometimes replaces middle-dots with control chars.
        line = re.sub(r"[\x00-\x1f\x7f•·∙⋅]+", "|", line)
        # Skip long prose / project descriptions
        if len(line) > 120 and not re.search(r"[,;|/]", line):
            continue
        # CEFR / native language lines under bare "Kenntnisse" belong in languages.
        if _LEVEL.search(line) and _parse_one_language(line) is not None:
            continue
        parts = re.split(r"\s*[,;|/]\s*", line)
        for part in parts:
            part = part.strip(" .")
            if part and not _is_heading_value(part) and len(part) < 80:
                if _LEVEL.search(part) and _parse_one_language(part) is not None:
                    continue
                skills.append(part)
    return list(dict.fromkeys(skills))


def _parse_mixed_languages_tools_mobility(body: str) -> tuple[list[LanguageEntry], list[str], list[str]]:
    lang_lines: list[str] = []
    soft_lines: list[str] = []
    lic: list[str] = []
    for raw in body.splitlines():
        line = _normalize_bullet(raw)
        if not line:
            continue
        if re.match(r"(?i)^(führerschein|fuehrerschein|driving\s+licen)", line):
            lic.extend(_inline_licence_mentions(line))
            continue
        if _LEVEL.search(line) and re.search(r"[A-Za-zÄÖÜäöüß]{3,}", line):
            # Language-looking if CEFR/native tokens present and not pure tool list
            if not re.search(r"(?i)\b(excel|sap|outlook|teams|power\s*bi|jira)\b", line) or _LEVEL.search(line):
                # Prefer language parse when CEFR present with language names
                if re.search(
                    r"(?i)\b(deutsch|englisch|französisch|spanisch|türkisch|tschechisch|"
                    r"german|english|french|spanish|italian|arabic|dutch|polish)\b",
                    line,
                ):
                    lang_lines.append(line)
                    continue
        soft_lines.append(line)
    return _parse_languages("\n".join(lang_lines)), _parse_software("\n".join(soft_lines)), lic


def parse_cv_text(text: str) -> dict[str, Any]:
    """Heuristic extraction — never invents values not present in text."""
    empty = {
        "raw_text_preview": text[:2000],
        "skills": [],
        "software": [],
        "languages": [],
        "education": [],
        "work_experience": [],
        "certificates": [],
        "driving_license": [],
        "experience_lines": [],
        "emails": [],
        "phones": [],
        "personal": {},
        "uncertain": [],
        "confidence": {},
    }
    if not text.strip():
        empty["confidence"] = {
            k: "Nicht erkannt"
            for k in (
                "skills",
                "software",
                "languages",
                "education",
                "work_experience",
                "certificates",
                "driving_license",
                "personal",
            )
        }
        return empty

    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phones = re.findall(r"(?:\+\d[\d\s\-()]{6,}\d)", text)
    # Also allow national numbers with leading 0 when clearly phone-sized
    phones += re.findall(r"(?<!\w)(?:0\d[\d\s\-()]{6,}\d)", text)
    sections = _split_named_sections(text)
    personal = _parse_personal_header(text, sections)

    languages = _parse_languages(sections.get("languages", ""))
    software = [
        s for s in _parse_software(sections.get("software", "")) if not _is_heading_value(s)
    ]
    skills = _parse_skills(sections.get("skills", ""))
    # Bare "Kenntnisse" maps to skills — recover only CEFR/native language lines.
    known = {(lang.language.lower(), (lang.level or "").lower()) for lang in languages}
    for raw in sections.get("skills", "").splitlines():
        line = _normalize_bullet(raw)
        if not line or not _LEVEL.search(line):
            continue
        entry = _parse_one_language(line)
        if entry is None:
            continue
        key = (entry.language.lower(), (entry.level or "").lower())
        if key not in known:
            languages.append(entry)
            known.add(key)
    certificates = [
        c for c in _parse_certificates(sections.get("certificates", "")) if not _is_heading_value(c.name)
    ]
    driving = _parse_driving(sections.get("license", ""))
    education, edu_certs = _parse_education(sections.get("education", ""))
    if edu_certs and not certificates:
        certificates.extend(edu_certs)
    elif edu_certs:
        existing = {c.name.lower() for c in certificates}
        for c in edu_certs:
            if c.name.lower() not in existing:
                certificates.append(c)
    experience = _parse_experience(sections.get("experience", ""))

    if "languages_tools_mobility" in sections:
        m_langs, m_soft, m_lic = _parse_mixed_languages_tools_mobility(
            sections["languages_tools_mobility"]
        )
        if m_langs and not languages:
            languages = m_langs
        if m_soft and not software:
            software = m_soft
        if m_lic and not driving:
            driving = m_lic

    # Fallback: only explicit licence phrases — never scan CEFR from full text.
    if not driving:
        driving = _inline_licence_mentions(text)

    uncertain: list[str] = []
    if driving and not all(re.fullmatch(r"[A-Z0-9]{1,3}", d) for d in driving):
        uncertain.append("driving_license")

    # Semantic confidence downgrades
    confidence = {
        "skills": field_confidence(skills),
        "software": field_confidence(software),
        "languages": field_confidence(languages),
        "education": field_confidence(education),
        "work_experience": field_confidence(experience),
        "certificates": field_confidence(certificates),
        "driving_license": field_confidence(driving),
        "personal": field_confidence(personal),
    }
    fn = (personal.get("first_name") or "").strip()
    ln = (personal.get("last_name") or "").strip()
    if fn and (_is_document_title(fn) or _is_heading_value(f"{fn} {ln}".strip()) or _is_document_title(f"{fn} {ln}")):
        confidence["personal"] = "low"
        uncertain.append("personal")
    for key in uncertain:
        if confidence.get(key) == "high":
            confidence[key] = "low"

    result = {
        "raw_text_preview": text[:2000],
        "skills": list(dict.fromkeys(skills)),
        "software": software,
        "languages": [
            {"language": lang.language, "level": lang.level, "source": "cv"}
            for lang in languages
        ],
        "education": [
            {
                "qualification": e.qualification,
                "institution": e.institution,
                "location": e.location,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "completion_date": e.completion_date,
                "source": "cv",
            }
            for e in education
        ],
        "work_experience": [
            {
                "title": e.title,
                "company": e.company,
                "location": e.location,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "responsibilities": e.responsibilities,
                "source": "cv",
            }
            for e in experience
        ],
        "certificates": [
            {"name": c.name, "issuer": c.issuer, "date": c.date, "source": "cv"}
            for c in certificates
        ],
        "driving_license": [{"value": d, "source": "cv"} for d in dict.fromkeys(driving)],
        "experience_lines": [e.label() for e in experience],
        "emails": list(dict.fromkeys(emails)),
        "phones": list(dict.fromkeys(p.strip() for p in phones)),
        "personal": personal,
        "uncertain": uncertain,
        "confidence": confidence,
    }
    return result


_HEADING_LINE = re.compile(
    r"^(Berufserfahrung|Berufliche Erfahrung|Beruflicher Werdegang|Ausbildung|"
    r"Weiterbildungen|Sprachen|Sprachkenntnisse|EDV|EDV-Kenntnisse|Führerschein|"
    r"Fähigkeiten|Kompetenzen|Kenntnisse|Experience|Education|Skills|"
    r"Professional Experience|Employment History|Career History|Employment|"
    r"Academic Background|Language Proficiency|Certifications|Certificates|"
    r"Tech Stack|Tools|Systems|Additional Skills|Core Skills|Key Skills|"
    r"Capabilities|Praxiserfahrung|Fahrerlaubnis|Qualifikation|Weiterbildung|"
    r"Persönliche Daten|Über mich|Profil|Zusammenfassung|Kontakt)\b",
    re.I,
)
_POSTAL_DE = re.compile(
    r"(?P<street>.+?)\s*,?\s*(?P<plz>\d{5})\s+(?P<city>[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-\s]+?)(?=,|$|\|)"
)
_POSTAL_UK_IE = re.compile(
    r"(?P<street>.+?)\s*[·|,]\s*(?P<city>[A-Za-z][A-Za-z\-\s]+?)\s+"
    r"(?P<pc>(?:[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}|[A-Z]\d{2}\s*[A-Z0-9]{4}))"
    r"(?:\s*,?\s*(?P<country>United Kingdom|Ireland|UK|IE))?",
    re.I,
)
_CITY_ONLY = re.compile(
    r"^(?P<city>[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-\s]{1,40})(?:\s*,\s*(?P<country>[A-Za-z][A-Za-z\s]+))?\s*(?:\||$)",
    re.I,
)
_DOB = re.compile(
    r"(?:Geburtsdatum|geboren(?:\s+am)?|DoB|Date of birth)\s*[:\-]?\s*"
    r"(?P<dob>\d{1,2}\.\d{1,2}\.\d{2,4})",
    re.I,
)
_NAME_RE = re.compile(
    r"^[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-']+(?:\s+[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-']+){1,3}$"
)


def _contains_name(text: str, personal: dict[str, str]) -> bool:
    full = f"{personal.get('first_name', '')} {personal.get('last_name', '')}".strip().lower()
    return bool(full) and full in (text or "").strip().lower()


def _parse_personal_header(text: str, sections: dict[str, str]) -> dict[str, str]:
    """Extract name/address from the CV header (before first known section)."""
    personal: dict[str, str] = {}
    header_lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if header_lines and not all(_is_document_title(x) for x in header_lines):
                break
            continue
        # Document titles must be skipped before heading detection so that
        # "Resume" / "Curriculum Vitae" / "PROFILE" never end the header early.
        if _is_document_title(line):
            continue
        if _HEADING_LINE.match(line) or _is_heading(line):
            break
        header_lines.append(line)
        if len(header_lines) >= 12:
            break

    for line in header_lines:
        if "@" in line or re.search(r"\+?\d[\d\s\-()]{7,}\d", line):
            continue
        if _DOB.search(line):
            continue
        if _is_heading_value(line) or _is_heading(line) or _is_document_title(line):
            continue
        # Reject ALL-CAPS multi-word titles that aren't typical names
        if line.isupper() and len(line.split()) >= 2:
            continue
        if _NAME_RE.fullmatch(line):
            parts = line.split()
            if 2 <= len(parts) <= 4:
                personal["first_name"] = parts[0]
                personal["last_name"] = " ".join(parts[1:])
                break

    for line in header_lines:
        # German PLZ
        m = _POSTAL_DE.search(line)
        if m:
            street = m.group("street").strip(" ,;·|")
            street = re.sub(r"^(Adresse|Anschrift)\s*[:\-]?\s*", "", street, flags=re.I)
            street = re.sub(r",?\s*(Germany|Deutschland|United Kingdom|Ireland)\s*$", "", street, flags=re.I)
            if "@" not in street and re.search(r"\d", street):
                personal["street"] = street
            personal["postal_code"] = m.group("plz")
            city = m.group("city").strip(" ,;·|")
            city = re.sub(r",?\s*(Germany|Deutschland)\s*$", "", city, flags=re.I).strip()
            personal["city"] = city
            hn = re.search(r"^(?P<s>.+?)\s+(?P<n>\d+[a-zA-Z]?)$", personal.get("street", ""))
            if hn:
                personal["house_number"] = hn.group("n")
            break

        m2 = _POSTAL_UK_IE.search(line)
        if m2:
            street = m2.group("street").strip(" ,;·|")
            street = re.sub(r"^(Adresse|Address)\s*[:\-]?\s*", "", street, flags=re.I)
            personal["street"] = street
            personal["city"] = m2.group("city").strip()
            personal["postal_code"] = re.sub(r"\s+", " ", m2.group("pc").strip().upper())
            if m2.group("country"):
                personal["country"] = m2.group("country").strip()
            hn = re.match(r"^(?P<n>\d+[a-zA-Z]?)\s+(?P<s>.+)$", street)
            if hn:
                personal["house_number"] = hn.group("n")
            break

    # City-only headers (deliberately incomplete contact data)
    if not personal.get("city"):
        for line in header_lines:
            # Prefer the segment before "|" when contact is "City | email"
            candidate = line.split("|", 1)[0].strip()
            if "@" in candidate or re.search(r"\d", candidate):
                continue
            # Do not treat the person's name line as a city.
            if personal.get("first_name") and _contains_name(candidate, personal):
                continue
            if _NAME_RE.fullmatch(candidate) and len(candidate.split()) >= 2:
                continue
            m3 = _CITY_ONLY.match(candidate) or _CITY_ONLY.match(line)
            if m3 and not re.search(r"\d", m3.group("city")):
                city = m3.group("city").strip()
                if city.lower() not in {"germany", "deutschland", "united kingdom", "ireland"}:
                    personal["city"] = city
                    if m3.group("country"):
                        personal["country"] = m3.group("country").strip()
                    break

    dob_m = _DOB.search(text)
    if dob_m:
        personal["date_of_birth"] = dob_m.group("dob")

    if personal.get("street") or personal.get("postal_code"):
        parts = [
            personal.get("street", ""),
            f"{personal.get('postal_code', '')} {personal.get('city', '')}".strip(),
        ]
        personal["address"] = ", ".join(p for p in parts if p)
    elif personal.get("city"):
        personal["address"] = personal["city"]
    return personal


def parsed_to_qualifications(parsed: dict[str, Any]) -> QualificationsConfig:
    def _as_sourced(items: list) -> list[dict[str, str]]:
        out = []
        for s in items or []:
            if isinstance(s, dict):
                val = str(s.get("value") or s.get("text") or "").strip()
                if val:
                    out.append({"value": val, "source": "cv"})
            elif str(s).strip():
                out.append({"value": str(s).strip(), "source": "cv"})
        return out

    return parse_qualifications(
        {
            "skills": _as_sourced(parsed.get("skills") or []),
            "software": _as_sourced(parsed.get("software") or []),
            "driving_license": _as_sourced(parsed.get("driving_license") or []),
            "languages": parsed.get("languages") or [],
            "education": parsed.get("education") or [],
            "work_experience": parsed.get("work_experience") or [],
            "certificates": parsed.get("certificates") or [],
        }
    )


def import_cv(path: Path) -> dict[str, Any]:
    text = extract_text(path)
    # Privacy: never log CV body at INFO — only path + length.
    logger.info("CV import: path=%s chars=%d", path.name, len(text or ""))
    parsed = parse_cv_text(text)
    parsed["source_path"] = str(path)
    return parsed
