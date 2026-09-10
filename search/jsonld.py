"""Shared JobPosting JSON-LD → Job mapping for HTML scrapers."""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from core.deduplicator import make_job_id
from core.models import Job, RemoteType


def _is_job_posting_type(type_value: Any) -> bool:
    if type_value == "JobPosting":
        return True
    if isinstance(type_value, list) and "JobPosting" in type_value:
        return True
    return False


def iter_job_postings(payload: Any) -> list[dict]:
    """Extract JobPosting dicts from a parsed JSON-LD document.

    Supports bare JobPosting objects, ``@graph`` arrays, and schema.org
    ``ItemList`` wrappers (common on StepStone/XING list pages).
    """
    items = payload if isinstance(payload, list) else [payload]
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if _is_job_posting_type(item.get("@type")):
            out.append(item)
        if item.get("@type") == "ItemList":
            for elem in item.get("itemListElement") or []:
                if not isinstance(elem, dict):
                    continue
                candidate = elem.get("item", elem)
                if isinstance(candidate, dict) and _is_job_posting_type(candidate.get("@type")):
                    out.append(candidate)
        for g in item.get("@graph") or []:
            if isinstance(g, dict) and _is_job_posting_type(g.get("@type")):
                out.append(g)
    return out


def job_from_list_card(
    *,
    source: str,
    title: str,
    url: str,
    company: str = "",
    city: str = "",
    min_title_len: int = 5,
) -> Job | None:
    """Build a Job from HTML card/link fallbacks when JSON-LD is absent."""
    title = (title or "").strip()
    url = (url or "").strip()
    if len(title) < min_title_len or not url:
        return None
    company = (company or "").strip()
    city = (city or "").strip()
    return Job(
        id=make_job_id(source, url, url, title, company),
        source=source,
        source_job_id=url,
        title=title,
        company=company,
        description="",
        city=city,
        address=city,
        remote_type=RemoteType.ONSITE.value,
        published_at="",
        url=url,
        application_url=url,
    )


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
