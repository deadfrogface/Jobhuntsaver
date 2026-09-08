"""Indeed Germany search via python-jobspy.

Pattern adapted from JobRadar jobspy_adapter.py (GPL-3.0).
"""

from __future__ import annotations

import logging
from datetime import datetime

from core.deduplicator import make_job_id
from core.models import Job, RemoteType
from search.base import JobSource, SearchQuery

logger = logging.getLogger("jobhuntsaver")


def _remote_from_row(row) -> str:
    loc = str(row.get("location") or "").lower()
    is_remote = row.get("is_remote")
    if is_remote or "remote" in loc or "homeoffice" in loc:
        if "hybrid" in loc:
            return RemoteType.HYBRID.value
        return RemoteType.REMOTE.value
    if "hybrid" in loc:
        return RemoteType.HYBRID.value
    return RemoteType.ONSITE.value


class IndeedSource(JobSource):
    source_id = "indeed"
    board = "indeed"

    def search(self, queries: list[SearchQuery]) -> list[Job]:
        try:
            from jobspy import scrape_jobs
        except ImportError as exc:
            raise RuntimeError("python-jobspy not installed") from exc

        all_jobs: list[Job] = []
        seen: set[str] = set()
        for query in queries:
            try:
                df = scrape_jobs(
                    site_name=[self.board],
                    search_term=query.keyword,
                    location=query.location if query.location.lower() != "remote" else "Germany",
                    country_indeed="germany",
                    results_wanted=query.max_results,
                    hours_old=max(24, query.published_within_days * 24),
                    is_remote=query.location.lower() == "remote",
                )
            except Exception as exc:
                logger.error("Indeed JobSpy error for '%s': %s", query.keyword, exc)
                continue
            if df is None or getattr(df, "empty", True):
                continue
            for _, row in df.iterrows():
                job = self._map_row(row)
                if job and job.id not in seen:
                    seen.add(job.id)
                    all_jobs.append(job)
        return all_jobs

    def _map_row(self, row) -> Job | None:
        title = str(row.get("title") or "").strip()
        if not title:
            return None
        url = str(row.get("job_url") or row.get("link") or "").strip()
        company = str(row.get("company") or "").strip()
        location = str(row.get("location") or "").strip()
        city = location.split(",")[0].strip() if location else ""
        description = str(row.get("description") or "")
        salary_text = ""
        salary_min = salary_max = None
        if row.get("min_amount"):
            try:
                salary_min = float(row.get("min_amount"))
                salary_max = float(row.get("max_amount")) if row.get("max_amount") else None
                salary_text = f"{salary_min}-{salary_max or '?'} {row.get('currency') or 'EUR'}"
            except (TypeError, ValueError):
                salary_text = str(row.get("min_amount"))
        dp = row.get("date_posted")
        if isinstance(dp, datetime):
            published = dp.date().isoformat()
        else:
            published = str(dp or "")
        source_job_id = str(row.get("id") or url)
        return Job(
            id=make_job_id(self.source_id, source_job_id, url, title, company),
            source=self.source_id,
            source_job_id=source_job_id,
            title=title,
            company=company,
            description=description,
            city=city,
            address=location,
            remote_type=_remote_from_row(row),
            employment_type=str(row.get("job_type") or ""),
            salary_min=salary_min,
            salary_max=salary_max,
            salary_text=salary_text,
            published_at=published,
            url=url,
            application_url=str(row.get("job_url_direct") or url),
        )


class LinkedInSearchSource(IndeedSource):
    source_id = "linkedin"
    board = "linkedin"

    def search(self, queries: list[SearchQuery]) -> list[Job]:
        # LinkedIn via JobSpy benefits from description fetch; handled inside jobspy when supported
        return super().search(queries)
