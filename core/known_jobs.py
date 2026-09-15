"""Global known-job suppression for search / apply.

Adapted from PBP stellen_zustand + stellen_dublette ideas (MIT): a prior
application case for the *same vacancy* blocks rediscovery as "new" and
blocks re-apply. Never blacklists an entire company when one vacancy was
rejected — only company+title and URL identities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from core.deduplicator import company_key, title_key
from core.lifecycle import KNOWN_SUPPRESS_STATUSES
from core.models import Job

if TYPE_CHECKING:
    from core.database import Database


@dataclass(frozen=True)
class KnownJobHit:
    case_id: str
    status: str
    company: str
    position: str
    reason: str


def _url_keys_for_job(job: Job) -> set[str]:
    from core.database import _url_identity

    keys = {_url_identity(u) for u in (job.url, job.application_url) if u}
    keys.discard("")
    return keys


def find_known_case(db: "Database", job: Job) -> KnownJobHit | None:
    """Return a suppressing ApplicationCase for this vacancy, if any.

    Match order: job_id → URL identity → company_key+title_key.
    Company-only matches are intentionally ignored (no company blacklist).
    """
    ck = company_key(job.company)
    tk = title_key(job.title)
    url_keys = _url_keys_for_job(job)

    if hasattr(db, "find_case_for_job"):
        hit = db.find_case_for_job(
            job_id=job.id or "",
            url_keys=url_keys,
            company_key=ck,
            title_key=tk,
            statuses=KNOWN_SUPPRESS_STATUSES,
        )
        if hit:
            return KnownJobHit(
                case_id=hit["id"],
                status=hit["status"],
                company=hit.get("company") or "",
                position=hit.get("position") or "",
                reason=hit.get("match_reason") or "known_case",
            )
    return None


def should_suppress_as_new(db: "Database", job: Job) -> tuple[bool, str]:
    """True when search must not count this job toward Jobs-pro-Suche as new."""
    if db.has_applied(job):
        return True, "already_applied_or_attempted"
    known = find_known_case(db, job)
    if known:
        return True, f"known_case:{known.status}:{known.case_id}"
    return False, ""


def refuse_reapply(db: "Database", job: Job) -> tuple[bool, str]:
    """Defense in depth for ApplicationManager — refuse even if search dedup failed."""
    if db.has_applied(job):
        return True, "already applied (safety)"
    known = find_known_case(db, job)
    if known:
        return (
            True,
            f"already applied (safety): known case {known.status} "
            f"for {known.company} / {known.position}",
        )
    return False, ""


def suppression_message(hit: KnownJobHit) -> str:
    """User-facing explanation (PBP stellen_zustand.nachricht style, condensed)."""
    return (
        f"Bereits erfasst als Bewerbungsfall ({hit.status}) bei "
        f"{hit.company} — {hit.position}. Keine erneute Entdeckung als neu."
    )
