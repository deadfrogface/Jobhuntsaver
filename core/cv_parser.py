"""CV / document text extraction without inventing qualifications.

Adapted from AutoApply core/document_parser.py (MIT).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("jobhuntsaver")

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}


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


def parse_cv_text(text: str) -> dict[str, Any]:
    """Heuristic extraction — never invents values not present in text."""
    result: dict[str, Any] = {
        "raw_text_preview": text[:2000],
        "skills": [],
        "languages": [],
        "education": [],
        "experience_lines": [],
        "emails": [],
        "phones": [],
    }
    if not text.strip():
        return result

    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phones = re.findall(r"(?:\+?\d[\d\s\-()]{7,}\d)", text)
    result["emails"] = list(dict.fromkeys(emails))
    result["phones"] = list(dict.fromkeys(p.strip() for p in phones))

    # Simple section scrape
    sections = _split_sections(text)
    for heading, body in sections:
        h = heading.lower()
        lines = [ln.strip(" -•\t") for ln in body.splitlines() if ln.strip()]
        if any(k in h for k in ("skill", "kenntnis", "kompetenz", "software")):
            tokens = []
            for line in lines:
                tokens.extend([t.strip() for t in re.split(r"[,|/]", line) if t.strip()])
            result["skills"].extend(tokens)
        elif any(k in h for k in ("language", "sprach")):
            result["languages"].extend(lines)
        elif any(k in h for k in ("education", "ausbildung", "studium", "schule")):
            result["education"].extend(lines)
        elif any(k in h for k in ("experience", "beruf", "tätigkeit", "employment", "arbeit")):
            result["experience_lines"].extend(lines)

    # Deduplicate while preserving order
    for key in ("skills", "languages", "education", "experience_lines"):
        result[key] = list(dict.fromkeys(result[key]))
    return result


def _split_sections(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    sections: list[tuple[str, str]] = []
    current_h = "general"
    buf: list[str] = []
    heading_re = re.compile(r"^(?:#{1,3}\s*)?([A-ZÄÖÜ][A-Za-zÄÖÜäöüß /&]{2,40})\s*:?\s*$")
    for line in lines:
        m = heading_re.match(line.strip())
        if m and len(line.strip()) < 48:
            if buf:
                sections.append((current_h, "\n".join(buf)))
            current_h = m.group(1)
            buf = []
        else:
            buf.append(line)
    if buf:
        sections.append((current_h, "\n".join(buf)))
    return sections


def import_cv(path: Path) -> dict[str, Any]:
    text = extract_text(path)
    parsed = parse_cv_text(text)
    parsed["source_path"] = str(path)
    return parsed
