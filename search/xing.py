"""XING Jobs discovery scraper.

Adapted from JobRadar xing.py (GPL-3.0).
"""

from __future__ import annotations

import json
import logging
import urllib.parse
from typing import Any

import httpx
from bs4 import BeautifulSoup

from core.deduplicator import make_job_id
from core.models import Job, RemoteType
from search.base import JobSource, SearchQuery

logger = logging.getLogger("jobhuntsaver")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9",
}


class XingSource(JobSource):
    source_id = "xing"

    def health_check(self) -> tuple[bool, str]:
        try:
            with httpx.Client(timeout=8.0, headers=_HEADERS) as client:
                r = client.get("https://www.xing.com/jobs", follow_redirects=True)
                return r.status_code < 500, f"HTTP {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def search(self, queries: list[SearchQuery]) -> list[Job]:
        all_jobs: list[Job] = []
        seen: set[str] = set()
        for query in queries:
            for job in self._search_one(query):
                if job.id not in seen:
                    seen.add(job.id)
                    all_jobs.append(job)
        return all_jobs

    def _search_one(self, query: SearchQuery) -> list[Job]:
        params = urllib.parse.urlencode(
            {"keywords": query.keyword, "location": query.location or "Deutschland"}
        )
        url = f"https://www.xing.com/jobs/search?{params}"
        jobs: list[Job] = []
        with httpx.Client(timeout=30.0, headers=_HEADERS, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                except Exception:
                    continue
                items = data if isinstance(data, list) else [data]
                for item in items:
                    candidates = []
                    if isinstance(item, dict) and item.get("@type") == "JobPosting":
                        candidates = [item]
                    elif isinstance(item, dict) and "@graph" in item:
                        candidates = item.get("@graph") or []
                    for g in candidates:
                        if isinstance(g, dict) and g.get("@type") == "JobPosting":
                            job = self.normalize(g)
                            if job:
                                jobs.append(job)
        return jobs[: query.max_results]

    def normalize(self, raw: Any) -> Job | None:
        item = raw if isinstance(raw, dict) else {}
        title = item.get("title") or ""
        if len(title) < 4:
            return None
        org = item.get("hiringOrganization") or {}
        company = org.get("name") if isinstance(org, dict) else ""
        url = item.get("url") or ""
        city = ""
        loc = item.get("jobLocation") or {}
        if isinstance(loc, list) and loc:
            loc = loc[0]
        if isinstance(loc, dict):
            addr = loc.get("address") or {}
            if isinstance(addr, dict):
                city = addr.get("addressLocality") or ""
        description = item.get("description") or ""
        text = BeautifulSoup(description, "lxml").get_text("\n", strip=True) if description else ""
        remote = RemoteType.ONSITE.value
        blob = f"{title} {text}".lower()
        if "remote" in blob or "homeoffice" in blob:
            remote = RemoteType.HYBRID.value if "hybrid" in blob else RemoteType.REMOTE.value
        return Job(
            id=make_job_id("xing", url, url, title, company or ""),
            source="xing",
            source_job_id=url,
            title=title,
            company=company or "",
            description=text,
            city=city,
            address=city,
            remote_type=remote,
            published_at=str(item.get("datePosted") or ""),
            url=url,
            application_url=url,
        )
