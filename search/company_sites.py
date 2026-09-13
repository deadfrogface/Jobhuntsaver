"""Company career pages placeholder source.

Unknown forms are left as needs_review — no aggressive scraping of arbitrary sites.
"""

from __future__ import annotations

from core.models import Job
from search.base import JobSource, SearchQuery


class CompanySitesSource(JobSource):
    source_id = "company_sites"

    def health_check(self) -> tuple[bool, str]:
        return True, "placeholder — Firmenkarriereseiten sind in v1 nicht implementiert"

    def search(self, queries: list[SearchQuery]) -> list[Job]:
        # Intentionally empty in v1 — curated company feeds can be added later.
        # Callers must treat this source as PLACEHOLDER, never OK_EMPTY.
        return []
