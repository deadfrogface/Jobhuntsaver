"""Duplicate detection and source preference."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from core.models import Job

# Prefer direct career / ATS over job portals when collapsing duplicates
SOURCE_PRIORITY = {
    "company_site": 100,
    "greenhouse": 90,
    "lever": 90,
    "ashby": 90,
    "workday": 90,
    "personio": 90,
    "smartrecruiters": 85,
    "successfactors": 85,
    "bundesagentur": 70,
    "stepstone": 50,
    "xing": 50,
    "indeed": 40,
    "linkedin": 40,
    "unknown": 10,
}


def make_job_id(source: str, source_job_id: str = "", url: str = "", title: str = "", company: str = "") -> str:
    key = source + "|" + (source_job_id or url.strip().lower() or f"{title}|{company}".lower())
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _norm(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9äöüß\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fingerprint(job: Job) -> str:
    """Soft fingerprint for cross-platform duplicates."""
    return "|".join(
        [
            _norm(job.company),
            _norm(job.title),
            _norm(job.city or job.address),
        ]
    )


def source_rank(job: Job) -> int:
    if job.ats_type and job.ats_type in SOURCE_PRIORITY:
        return SOURCE_PRIORITY[job.ats_type]
    return SOURCE_PRIORITY.get(job.source, 10)


def deduplicate(jobs: list[Job]) -> list[Job]:
    """Keep one main entry per vacancy; attach alt sources on the winner."""
    by_hard: dict[str, Job] = {}
    hard_losers: list[Job] = []
    for job in jobs:
        hard_key = job.url.strip().lower() or job.application_url.strip().lower() or job.id
        existing = by_hard.get(hard_key)
        if not existing:
            by_hard[hard_key] = job
            continue
        if source_rank(job) > source_rank(existing):
            job.alt_sources = list({*existing.alt_sources, existing.source, *job.alt_sources})
            existing.duplicate_of = job.id
            hard_losers.append(existing)
            by_hard[hard_key] = job
        else:
            existing.alt_sources = list({*existing.alt_sources, job.source})
            job.duplicate_of = existing.id
            hard_losers.append(job)

    # Soft fingerprint grouping across different URLs
    groups: dict[str, list[Job]] = defaultdict(list)
    for job in by_hard.values():
        if job.duplicate_of:
            continue
        groups[fingerprint(job)].append(job)

    winners: list[Job] = []
    for _fp, group in groups.items():
        if len(group) == 1:
            winners.append(group[0])
            continue
        group.sort(key=source_rank, reverse=True)
        primary = group[0]
        for other in group[1:]:
            other.duplicate_of = primary.id
            primary.alt_sources = list({*primary.alt_sources, other.source, *other.alt_sources})
            winners.append(other)  # keep internally, marked duplicate
        winners.append(primary)
    # Preserve hard-URL losers so callers can count duplicates_removed.
    return winners + hard_losers


def is_likely_same_job(a: Job, b: Job) -> bool:
    if a.id and b.id and a.id == b.id:
        return True
    if a.url and b.url and a.url.strip().lower() == b.url.strip().lower():
        return True
    if a.application_url and b.application_url and a.application_url.strip().lower() == b.application_url.strip().lower():
        return True
    return fingerprint(a) == fingerprint(b) and bool(fingerprint(a).strip("|"))
