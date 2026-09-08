"""CV / document text extraction and structured profile parsing.

No paid AI. Never invents qualifications that are not present in the text.
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

logger = logging.getLogger("jobhuntsaver")

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}

_DATE = r"(?:\d{1,2}\.\d{1,2}\.\d{2,4}|\d{2}\.\d{4}|\d{4})"
_PERIOD = re.compile(
    rf"(?P<start>Seit\s+{_DATE}|{_DATE})\s*[–\-—]\s*(?P<end>{_DATE}|heute|aktuell|present)",
    re.IGNORECASE,
)
_SINCE = re.compile(rf"^Seit\s+(?P<start>{_DATE})\s*$", re.IGNORECASE)
_ABSCHLUSS = re.compile(
    rf"Abschluss\s*:\s*(?P<date>{_DATE})",
    re.IGNORECASE,
)
_LEVEL = re.compile(r"\b([ABC][12]|Muttersprache|native)\b", re.IGNORECASE)
_HEADINGS = {
    "experience": (
        "berufserfahrung",
        "berufliche erfahrung",
        "experience",
        "tätigkeiten",
        "beschäftigung",
    ),
    "education": ("ausbildung", "schulbildung", "schule", "studium", "education"),
    "certificates": (
        "weiterbildungen",
        "weiterbildung",
        "zertifikate",
        "zertifikat",
        "fortbildung",
        "licenses",
        "zertifizierung",
    ),
    "languages": ("sprachen", "languages", "sprachkenntnisse"),
    "software": (
        "edv-kenntnisse",
        "edv",
        "it-kenntnisse",
        "software",
        "kenntnisse",
        "it skills",
        "computerkenntnisse",
    ),
    "license": ("führerschein", "fuehrerschein", "driving licence", "driving license"),
    "skills": ("fähigkeiten", "kompetenzen", "skills", "stärken"),
}


def extract_text(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")
    if ext == ".pdf":
        return _extract_from_pdf(file_path)
    if ext in (".docx", ".doc"):
        return _extract_from_docx(file_path)
    return file_path.read_text(encoding="utf-8", errors="replace")


def _extract_from_pdf(file_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install pypdf for PDF extraction") from exc
    reader = PdfReader(str(file_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    return "\n\n".join(pages)


def _extract_from_docx(file_path: Path) -> str:
    from docx import Document

    doc = Document(str(file_path))
    return "\n\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())


def _normalize_bullet(line: str) -> str:
    return re.sub(r"^[\s•\-–—*·]+", "", line).strip()


def _is_heading(line: str) -> str | None:
    cleaned = line.strip().lower().rstrip(":")
    if not cleaned or len(cleaned) > 48:
        return None
    for key, aliases in _HEADINGS.items():
        if cleaned in aliases:
            return key
    return None


def _split_named_sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    sections: dict[str, list[str]] = {"general": []}
    current = "general"
    for raw in lines:
        line = raw.strip()
        if not line:
            sections.setdefault(current, []).append("")
            continue
        heading = _is_heading(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        # Skip document title lines such as "Lebenslauf" / "Curriculum Vitae"
        if re.fullmatch(r"(tabellarischer\s+)?lebenslauf|curriculum\s+vitae", line, re.I):
            continue
        sections.setdefault(current, []).append(raw.rstrip())
    return {k: "\n".join(v).strip() for k, v in sections.items() if "".join(v).strip()}


def _parse_languages(body: str) -> list[LanguageEntry]:
    results: list[LanguageEntry] = []
    for raw in body.splitlines():
        line = _normalize_bullet(raw)
        if not line:
            continue
        # "Dänisch & Schwedisch – A2" (multiple languages, one level)
        amp = re.match(
            r"^(?P<langs>.+?)\s*[–\-—|]\s*(?P<level>[ABC][12]|Muttersprache|native)\s*$",
            line,
            re.I,
        )
        if amp and ("&" in amp.group("langs") or " und " in amp.group("langs").lower()):
            level = amp.group("level")
            parts = re.split(r"\s*(?:&| und )\s*", amp.group("langs"), flags=re.I)
            for part in parts:
                name = re.sub(r"\(.*?\)", "", part).strip(" -–—|")
                if name:
                    results.append(LanguageEntry(language=name, level=level.upper() if len(level) == 2 else level))
            continue
        # "Deutsch (Muttersprache) – C2" / "Englisch – C1"
        m = re.match(
            r"^(?P<lang>[A-Za-zÄÖÜäöüß /]+?)(?:\s*\((?P<meta>[^)]+)\))?\s*[–\-—|]?\s*(?P<level>[ABC][12]|Muttersprache|native)?\s*$",
            line,
            re.I,
        )
        if m:
            lang = m.group("lang").strip()
            level = (m.group("level") or "").strip()
            meta = (m.group("meta") or "").strip()
            if not level and meta and _LEVEL.search(meta):
                level = _LEVEL.search(meta).group(1)
            elif not level and meta.lower() in {"muttersprache", "native"}:
                level = "C2"
            if lang:
                results.append(
                    LanguageEntry(
                        language=lang,
                        level=level.upper() if re.fullmatch(r"[ABC][12]", level, re.I) else level,
                    )
                )
            continue
        level_m = _LEVEL.search(line)
        if level_m:
            lang = line[: level_m.start()].strip(" -–—|()")
            if lang:
                results.append(LanguageEntry(language=lang, level=level_m.group(1).upper()))
    # Deduplicate by language
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
        if not line:
            continue
        # Expand "MS Office (Word, Excel – fortgeschritten)"
        m = re.match(r"^(?P<head>MS Office)\s*\((?P<inner>.+)\)$", line, re.I)
        if m:
            items.append(m.group("head"))
            inner = m.group("inner")
            # Word, Excel – fortgeschritten
            chunks = re.split(r",|/", inner)
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                if "excel" in chunk.lower():
                    items.append("Excel – fortgeschritten" if "fortgeschritten" in chunk.lower() or "fortgeschritten" in inner.lower() else "Excel")
                    if "fortgeschritten" in inner.lower() and "excel" in chunk.lower():
                        pass
                elif "word" in chunk.lower():
                    items.append("Word")
                else:
                    items.append(chunk)
            # If fortgeschritten applies to Excel specifically already handled
            continue
        # Comma-separated tools on one line, e.g. "Power BI, Microsoft Teams"
        if "," in line and not re.search(r"\(.+,.+\)", line):
            for part in line.split(","):
                part = part.strip()
                if part:
                    items.append(part)
            continue
        # "Long description (ShortName)"
        paren = re.match(r"^(?P<desc>.+?)\s*\((?P<name>[^)]+)\)\s*$", line)
        if paren and len(paren.group("name")) < 40:
            items.append(f"{paren.group('name').strip()} / {paren.group('desc').strip()}")
            items.append(paren.group("name").strip())
            continue
        items.append(line)
    # Cleanup duplicates preserving order; keep richer excel entry
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        # Prefer "Excel – fortgeschritten" over "Excel"
        if item.lower() == "excel" and any("excel" in c.lower() and "fortgeschritten" in c.lower() for c in items):
            continue
        seen.add(key)
        cleaned.append(item)
    return cleaned


def _parse_certificates(body: str) -> list[CertificateEntry]:
    result: list[CertificateEntry] = []
    for raw in body.splitlines():
        line = _normalize_bullet(raw)
        if line:
            result.append(CertificateEntry(name=line))
    return result


def _parse_driving(body: str) -> list[str]:
    result: list[str] = []
    for raw in body.splitlines():
        line = _normalize_bullet(raw)
        if not line:
            continue
        if re.search(r"klasse\s*[A-Z0-9]+", line, re.I) or re.search(r"\b[ABE]\b", line):
            result.append(line)
        elif "führerschein" not in line.lower():
            result.append(line)
    if not result and body.strip():
        result.append(_normalize_bullet(body.splitlines()[0]))
    return list(dict.fromkeys(result))


_QUAL_START = re.compile(
    r"^(Berufsausbildung|Mittlere Reife|Fachhochschulreife|Abitur|Bachelor|Master|"
    r"Studium|Fachabitur|Realschulabschluss|Hauptschulabschluss|Promotion)",
    re.IGNORECASE,
)


def _parse_education(body: str) -> list[EducationEntry]:
    lines = [ln.rstrip() for ln in body.splitlines()]
    entries: list[EducationEntry] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith(("•", "-", "–")):
            i += 1
            continue
        if line.lower().startswith("abschluss"):
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
            if _is_heading(nxt) or _QUAL_START.match(nxt):
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
    return [e for e in entries if e.qualification]


def _parse_experience(body: str) -> list[ExperienceEntry]:
    lines = [ln.rstrip() for ln in body.splitlines()]
    entries: list[ExperienceEntry] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        start = end = ""
        pm = _PERIOD.search(line)
        sm = _SINCE.match(line)
        if pm:
            start = pm.group("start").replace("Seit ", "").replace("seit ", "").strip()
            end = pm.group("end").strip()
            i += 1
        elif sm:
            start = sm.group("start")
            end = "aktuell"
            i += 1
        else:
            # date on its own previous style already handled; skip orphan bullets
            if line.startswith(("•", "-", "–", "*")):
                i += 1
                continue
            # Maybe title without date — uncertain, skip inventing
            i += 1
            continue

        # Skip blanks
        while i < len(lines) and not lines[i].strip():
            i += 1
        title = lines[i].strip() if i < len(lines) else ""
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        company_line = lines[i].strip() if i < len(lines) else ""
        company = company_line
        location = ""
        if company_line and not company_line.startswith(("•", "-", "–", "*")):
            i += 1
            if "," in company_line:
                company, location = [p.strip() for p in company_line.rsplit(",", 1)]
        responsibilities: list[str] = []
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt:
                i += 1
                # blank: peek if next is a new period
                if i < len(lines) and (_PERIOD.search(lines[i].strip()) or _SINCE.match(lines[i].strip())):
                    break
                continue
            if _PERIOD.search(nxt) or _SINCE.match(nxt):
                break
            if _is_heading(nxt):
                break
            if nxt.startswith(("•", "-", "–", "*", "·")) or True:
                # Responsibilities are typically bullets; also accept plain lines under a job
                if _PERIOD.search(nxt) or _SINCE.match(nxt):
                    break
                # Stop if this looks like a new job title+company without date (rare)
                cleaned = _normalize_bullet(nxt)
                if cleaned:
                    responsibilities.append(cleaned)
                i += 1
                continue
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
    }
    if not text.strip():
        return empty

    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phones = re.findall(r"(?:\+?\d[\d\s\-()]{7,}\d)", text)
    sections = _split_named_sections(text)
    personal = _parse_personal_header(text, sections)

    languages = _parse_languages(sections.get("languages", ""))
    software = _parse_software(sections.get("software", ""))
    # If "kenntnisse" caught soft skills separately
    skills = []
    if "skills" in sections:
        for raw in sections["skills"].splitlines():
            line = _normalize_bullet(raw)
            if line:
                skills.extend([p.strip() for p in re.split(r"[,|/]", line) if p.strip()])
    certificates = _parse_certificates(sections.get("certificates", ""))
    driving = _parse_driving(sections.get("license", ""))
    education = _parse_education(sections.get("education", ""))
    experience = _parse_experience(sections.get("experience", ""))

    # Fallback: scan whole text for Führerschein if section missing
    if not driving:
        for m in re.finditer(r"Klasse\s+[A-Z0-9]+(?:\s*\([^)]+\))?", text, re.I):
            driving.append(m.group(0))

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
        "uncertain": [],
    }
    return result


_HEADING_LINE = re.compile(
    r"^(Berufserfahrung|Ausbildung|Weiterbildungen|Sprachen|EDV|Führerschein|"
    r"Fähigkeiten|Kompetenzen|Kenntnisse|Experience|Education|Skills)\b",
    re.I,
)
_POSTAL_CITY = re.compile(
    r"(?P<street>.+?)\s*,?\s*(?P<plz>\d{5})\s+(?P<city>[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-\s]+)"
)
_DOB = re.compile(
    r"(?:Geburtsdatum|geboren(?:\s+am)?|DoB|Date of birth)\s*[:\-]?\s*"
    r"(?P<dob>\d{1,2}\.\d{1,2}\.\d{2,4})",
    re.I,
)


def _parse_personal_header(text: str, sections: dict[str, str]) -> dict[str, str]:
    """Extract name/address from the CV header (before first known section)."""
    personal: dict[str, str] = {}
    header_lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if header_lines:
                break
            continue
        if _HEADING_LINE.match(line):
            break
        # Skip obvious non-name contact-only lines later
        header_lines.append(line)
        if len(header_lines) >= 12:
            break

    # Name: first line that looks like 2+ words and is not email/phone/address-heavy
    for line in header_lines:
        if "@" in line or re.search(r"\d{5}", line) or re.search(r"\+?\d[\d\s\-()]{7,}\d", line):
            continue
        if _DOB.search(line):
            continue
        if re.fullmatch(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-]+)+", line):
            parts = line.split()
            if 2 <= len(parts) <= 4:
                personal["first_name"] = parts[0]
                personal["last_name"] = " ".join(parts[1:])
                break

    for line in header_lines:
        m = _POSTAL_CITY.search(line)
        if m:
            street = m.group("street").strip(" ,;")
            # Drop leading labels
            street = re.sub(r"^(Adresse|Anschrift)\s*[:\-]?\s*", "", street, flags=re.I)
            if street and not re.search(r"@", street):
                personal["street"] = street
            personal["postal_code"] = m.group("plz")
            personal["city"] = m.group("city").strip(" ,;")
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
    parsed = parse_cv_text(text)
    parsed["source_path"] = str(path)
    return parsed
