"""Shared JobPosting JSON-LD → Job mapping for HTML scrapers."""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from core.deduplicator import make_job_id
from core.models import Job, RemoteType


def iter_job_postings(payload: Any) -> list[dict]:
    """Extract JobPosting dicts from a parsed JSON-LD document."""
    items = payload if isinstance(payload, list) else [payload]
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("@type") in ("JobPosting", ["JobPosting"]) or item.get("@type") == "JobPosting":
            out.append(item)
        for g in item.get("@graph") or []:
            if isinstance(g, dict) and g.get("@type") == "JobPosting":
                out.append(g)
    return out


def job_from_job_posting(
    item: dict,
    *,
    source: str,
    min_title_len: int = 1,
) -> Job | None:
    """Normalize a schema.org JobPosting object into a Job."""
    title = str(item.get("title") or "").strip()
    if len(title) < min_title_len:
        return None
    org = item.get("hiringOrganization") or {}
    company = ""
    if isinstance(org, dict):
        company = str(org.get("name") or "").strip()
    url = item.get("url") or item.get("mainEntityOfPage") or ""
    if isinstance(url, dict):
        url = url.get("@id") or ""
    url = str(url or "").strip()
    city = ""
    loc = item.get("jobLocation") or {}
    if isinstance(loc, list) and loc:
        loc = loc[0]
    if isinstance(loc, dict):
        addr = loc.get("address") or {}
        if isinstance(addr, dict):
            city = str(addr.get("addressLocality") or "").strip()
    description = item.get("description") or ""
    text = (
        BeautifulSoup(description, "lxml").get_text("\n", strip=True) if description else ""
    )
    remote = RemoteType.ONSITE.value
    blob = f"{title} {text}".lower()
    if "remote" in blob or "homeoffice" in blob:
        remote = RemoteType.HYBRID.value if "hybrid" in blob else RemoteType.REMOTE.value
    return Job(
        id=make_job_id(source, url, url, title, company),
        source=source,
        source_job_id=url,
        title=title,
        company=company,
        description=text,
        city=city,
        address=city,
        remote_type=remote,
        published_at=str(item.get("datePosted") or ""),
        url=url,
        application_url=url,
    )
