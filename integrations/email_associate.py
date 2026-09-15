"""Associate emails with ApplicationCase rows.

Adapted from PBP ``match_email_to_application`` (MIT): domain-signal required,
high threshold, recruiter-domain ambiguity → leave unlinked for review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urlparse

from integrations.email_normalize import extract_sender_domain, extract_sender_email


# PBP RECRUITER_DOMAIN_KEYWORDS (MIT) — never domain-only match.
RECRUITER_DOMAIN_KEYWORDS: tuple[str, ...] = (
    "hays",
    "sthree",
    "randstad",
    "adecco",
    "gulp",
    "ferchau",
    "brunel",
    "akkodis",
    "manpower",
    "michaelpage",
    "robertwalters",
    "computerfutures",
    "huxley",
    "westhouse",
    "etengo",
    "solcom",
)

AUTO_MATCH_THRESHOLD = 0.90
ARCHIVE_STATUSES = frozenset({"rejected", "withdrawn", "closed", "abgelehnt", "zurueckgezogen"})


@dataclass(frozen=True)
class AssociationResult:
    case_id: str | None
    confidence: float
    ambiguous: bool
    candidates: tuple[str, ...] = ()
    reason: str = ""


def _is_recruiter_domain(domain: str) -> bool:
    d = (domain or "").lower()
    return bool(d) and any(k in d for k in RECRUITER_DOMAIN_KEYWORDS)


def _company_in_text(company: str, text: str) -> bool:
    c = (company or "").strip().lower()
    if len(c) < 3:
        return False
    return c in (text or "").lower()


def associate_email(
    *,
    sender: str,
    subject: str,
    cases: Iterable[dict[str, Any]],
    direction: str = "inbound",
    recipients: str = "",
) -> AssociationResult:
    """Return best case link or ambiguous/unlinked (Im Zweifel unverknüpft)."""
    cases_list = list(cases)
    if not cases_list:
        return AssociationResult(None, 0.0, False, reason="no_cases")

    sender_email = extract_sender_email(sender)
    sender_domain = extract_sender_domain(sender)
    subject_l = (subject or "").lower()
    match_text = (recipients or "").lower() if direction == "outbound" else (sender or "").lower()

    candidates: list[dict[str, Any]] = []
    for app in cases_list:
        score = 0.0
        has_domain = False
        has_content = False
        exact_email = False
        company = (app.get("company") or "").lower()
        kontakt = (app.get("contact_email") or app.get("kontakt_email") or "").lower()
        contact_name = (app.get("contact_name") or app.get("ansprechpartner") or "").lower()
        title = (app.get("position") or app.get("title") or "").lower()
        app_url = (app.get("url") or app.get("application_url") or "").lower()
        status = (app.get("status") or "").lower()

        if kontakt and kontakt == sender_email:
            score = max(score, 0.95)
            has_domain = True
            has_content = True
            exact_email = True

        if kontakt and "@" in kontakt:
            app_domain = kontakt.split("@", 1)[1]
            if sender_domain and sender_domain == app_domain:
                score = max(score, 0.9)
                has_domain = True

        if company and len(company) > 2:
            if company in match_text:
                score = max(score, 0.7)
            if company in subject_l:
                score = max(score, 0.65)
            compact = company.replace(" ", "").replace("-", "")
            if sender_domain and compact and compact in sender_domain.replace("-", ""):
                score = max(score, 0.9)
                has_domain = True

        if title and len(title) > 4:
            words = [w for w in title.split() if len(w) > 3]
            if words:
                matches = sum(1 for w in words if w in subject_l)
                if matches >= 2 or (matches >= 1 and len(words) <= 2):
                    score = max(score, 0.6)
                    has_content = True

        if contact_name and len(contact_name) > 3:
            parts = [p for p in contact_name.split() if len(p) > 2]
            if parts and all(p in match_text for p in parts):
                score = max(score, 0.5)
                has_content = True

        if app_url and sender_domain:
            try:
                host = (urlparse(app_url).netloc or "").lower()
            except Exception:
                host = ""
            if host and (sender_domain in host or host.endswith(sender_domain)):
                score = max(score, 0.85)
                has_domain = True

        if score > 0:
            candidates.append(
                {
                    "case_id": app.get("id"),
                    "score": score,
                    "domain_signal": has_domain,
                    "content_signal": has_content,
                    "exact_email": exact_email,
                    "archived": status in ARCHIVE_STATUSES,
                }
            )

    if not candidates:
        return AssociationResult(None, 0.0, False, reason="no_candidate")

    eligible = [c for c in candidates if not c["archived"] or c["exact_email"]]
    if not eligible:
        return AssociationResult(
            None,
            0.0,
            True,
            tuple(str(c["case_id"]) for c in candidates if c["case_id"]),
            reason="only_archived",
        )

    best = max(eligible, key=lambda c: (c["score"], c["content_signal"], c["domain_signal"]))
    if best["score"] < AUTO_MATCH_THRESHOLD or not best["domain_signal"]:
        return AssociationResult(
            None,
            float(best["score"]),
            True,
            tuple(str(c["case_id"]) for c in eligible if c["case_id"]),
            reason="below_threshold_or_no_domain",
        )

    if not best["content_signal"]:
        domain_hits = [c for c in eligible if c["domain_signal"]]
        with_content = [
            c for c in domain_hits if c["content_signal"] and c["score"] >= AUTO_MATCH_THRESHOLD
        ]
        if len(with_content) == 1:
            best = with_content[0]
        elif len(domain_hits) >= 2 or _is_recruiter_domain(sender_domain):
            return AssociationResult(
                None,
                float(best["score"]),
                True,
                tuple(str(c["case_id"]) for c in domain_hits if c["case_id"]),
                reason="ambiguous_domain",
            )

    return AssociationResult(
        str(best["case_id"]) if best["case_id"] else None,
        round(float(best["score"]), 2),
        False,
        reason="auto_match",
    )
