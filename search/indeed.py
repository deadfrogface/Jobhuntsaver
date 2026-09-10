"""Indeed Germany search via python-jobspy.

Pattern adapted from JobRadar jobspy_adapter.py (GPL-3.0).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

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

    def health_check(self) -> tuple[bool, str]:
        try:
            import tls_client  # noqa: F401
            import jobspy  # noqa: F401
        except ImportError as exc:
            return False, f"missing dependency: {exc}"
        except OSError as exc:
            return False, f"native library error: {exc}"
        return True, "ok"

    def search(self, queries: list[SearchQuery]) -> list[Job]:
        try:
            # tls_client ships native DLLs required by python-jobspy on Windows.
            import tls_client  # noqa: F401
            from jobspy import scrape_jobs
        except ImportError as exc:
            raise RuntimeError(
                f"Indeed dependency missing (python-jobspy/tls_client): {exc}"
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"Indeed native library failed to load (tls_client DLL): {exc}"
            ) from exc

        all_jobs: list[Job] = []
        seen: set[str] = set()
        hard_errors: list[str] = []
        for query in queries:
            try:
                kwargs = dict(
                    site_name=[self.board],
                    search_term=query.keyword,
                    location=query.location if query.location.lower() != "remote" else "Germany",
                    country_indeed="germany",
                    results_wanted=query.max_results,
                    is_remote=query.location.lower() == "remote",
                    distance=int(query.radius_km) if query.radius_km else None,
                )
                try:
                    df = scrape_jobs(**kwargs)
                except TypeError:
                    # Older/newer jobspy builds differ slightly in kwargs
                    kwargs.pop("distance", None)
                    df = scrape_jobs(**kwargs)
            except Exception as exc:
                logger.error("Indeed JobSpy error for '%s': %s", query.keyword, exc)
                msg = str(exc)
                if any(
                    x in msg.lower()
                    for x in ("dynlib", "dll", "unexpected keyword", "missing")
                ):
                    hard_errors.append(msg)
                    continue
                hard_errors.append(msg)
                continue
            if df is None or getattr(df, "empty", True):
                continue
            for _, row in df.iterrows():
                job = self.normalize(row)
                if job and job.id not in seen:
                    seen.add(job.id)
                    all_jobs.append(job)
        if not all_jobs and hard_errors:
            raise RuntimeError(hard_errors[0])
        return all_jobs

    def normalize(self, raw: Any) -> Job | None:
        row = raw
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


