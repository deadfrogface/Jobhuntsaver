"""StepStone Germany discovery scraper.

Adapted from JobRadar stepstone.py (GPL-3.0).
"""

from __future__ import annotations

import json
import logging
import urllib.parse

import httpx
from bs4 import BeautifulSoup

from core.deduplicator import make_job_id
from core.models import Job, RemoteType
from search.base import JobSource, SearchQuery

logger = logging.getLogger("jobhuntsaver")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}


class StepstoneSource(JobSource):
    source_id = "stepstone"

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
        q = urllib.parse.quote(query.keyword)
        loc = urllib.parse.quote(query.location or "")
        url = f"https://www.stepstone.de/jobs/{q}/in-{loc}" if loc else f"https://www.stepstone.de/jobs/{q}"
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
                    if isinstance(item, dict) and item.get("@type") in ("JobPosting", ["JobPosting"]):
                        job = self._from_jsonld(item)
                        if job:
                            jobs.append(job)
                    if isinstance(item, dict) and "@graph" in item:
                        for g in item["@graph"]:
                            if isinstance(g, dict) and g.get("@type") == "JobPosting":
                                job = self._from_jsonld(g)
                                if job:
                                    jobs.append(job)
        return jobs[: query.max_results]

    def _from_jsonld(self, item: dict) -> Job | None:
        title = item.get("title") or ""
        if not title:
            return None
        company = ""
        org = item.get("hiringOrganization") or {}
        if isinstance(org, dict):
            company = org.get("name") or ""
        url = item.get("url") or item.get("mainEntityOfPage") or ""
        if isinstance(url, dict):
            url = url.get("@id") or ""
        loc = item.get("jobLocation") or {}
        city = ""
        if isinstance(loc, list) and loc:
            loc = loc[0]
        if isinstance(loc, dict):
            addr = loc.get("address") or {}
            if isinstance(addr, dict):
                city = addr.get("addressLocality") or ""
        description = item.get("description") or ""
        remote = RemoteType.ONSITE.value
        blob = f"{title} {description}".lower()
        if "remote" in blob or "homeoffice" in blob:
            remote = RemoteType.REMOTE.value if "hybrid" not in blob else RemoteType.HYBRID.value
        return Job(
            id=make_job_id("stepstone", url, url, title, company),
            source="stepstone",
            source_job_id=url,
            title=title,
            company=company,
            description=BeautifulSoup(description, "lxml").get_text("\n", strip=True) if description else "",
            city=city,
            address=city,
            remote_type=remote,
            published_at=str(item.get("datePosted") or ""),
            url=url,
            application_url=url,
        )
