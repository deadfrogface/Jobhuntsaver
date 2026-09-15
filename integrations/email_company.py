"""Lightweight company / ATS hints from email (offline rules).

Heuristics adapted from GmailJobTracker ats_detection_heuristics +
CompanyResolver.normalize ideas (MIT). Does not pull Django or ML.
"""

from __future__ import annotations

import re
from typing import Optional

from core.text_normalize import clean_company

ATS_URL_PATTERNS: list[tuple[str, str]] = [
    (r"myworkday(?:jobs)?\.com", "workday"),
    (r"boards\.greenhouse\.io", "greenhouse"),
    (r"greenhouse\.io", "greenhouse"),
    (r"jobs\.lever\.co", "lever"),
    (r"hire\.lever\.co", "lever"),
    (r"icims\.com", "icims"),
    (r"taleo\.net", "taleo"),
    (r"smartrecruiters\.com", "smartrecruiters"),
    (r"jobvite\.com", "jobvite"),
    (r"successfactors\.com", "successfactors"),
    (r"jobs\.ashbyhq\.com", "ashby"),
    (r"ashbyhq\.com", "ashby"),
    (r"personio\.(?:de|com)", "personio"),
    (r"indeed\.com", "indeed"),
    (r"linkedin\.com", "linkedin"),
]

ATS_SENDER_DOMAINS: tuple[str, ...] = (
    "greenhouse.io",
    "greenhouse-mail.io",
    "lever.co",
    "hire.lever.co",
    "ashbyhq.com",
    "myworkday.com",
    "myworkdayjobs.com",
    "icims.com",
    "smartrecruiters.com",
    "jobvite.com",
    "bamboohr.com",
    "workablemail.com",
    "recruitee.com",
    "breezy.hr",
    "personio.de",
    "personio.com",
)


def detect_ats_from_text(text: str) -> Optional[str]:
    blob = text or ""
    for pattern, name in ATS_URL_PATTERNS:
        if re.search(pattern, blob, re.I):
            return name
    return None


def is_ats_sender_domain(domain: str) -> bool:
    d = (domain or "").lower()
    return any(d == a or d.endswith("." + a) for a in ATS_SENDER_DOMAINS)


def normalize_company_name(name: str) -> str:
    """Strip common subject artifacts then clean_company."""
    value = name or ""
    value = re.sub(r"^(re|fw|aw|wg)\s*:\s*", "", value, flags=re.I)
    value = re.sub(r"\s+[-–|].*$", "", value)
    return clean_company(value)


_COMPANY_SUBJECT_PATTERNS = [
    re.compile(r"bewerbung\s+bei\s+(.+?)(?:\s+[-–|]|$)", re.I),
    re.compile(r"application\s+(?:to|at)\s+(.+?)(?:\s+[-–|]|$)", re.I),
    re.compile(r"your\s+application\s+to\s+(.+?)(?:\s+[-–|]|$)", re.I),
]


def extract_company_from_subject(subject: str) -> str:
    for rx in _COMPANY_SUBJECT_PATTERNS:
        m = rx.search(subject or "")
        if m:
            return normalize_company_name(m.group(1))
    return ""
