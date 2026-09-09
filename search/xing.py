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

from core.models import Job
from search.base import JobSource, SearchQuery
from search.jsonld import iter_job_postings, job_from_job_posting

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
                for item in iter_job_postings(data):
                    job = self.normalize(item)
                    if job:
                        jobs.append(job)
        return jobs[: query.max_results]

    def normalize(self, raw: Any) -> Job | None:
        return job_from_job_posting(
            raw if isinstance(raw, dict) else {},
            source=self.source_id,
            min_title_len=4,
        )
