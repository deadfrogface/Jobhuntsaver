"""LinkedIn job discovery via JobSpy (Indeed-compatible board).

Single canonical adapter — registry and tests import from here.
"""

from __future__ import annotations

from core.models import Job
from search.base import SearchQuery
from search.indeed import IndeedSource


class LinkedInSearchSource(IndeedSource):
    source_id = "linkedin"
    board = "linkedin"

    def search(self, queries: list[SearchQuery]) -> list[Job]:
        # LinkedIn via JobSpy; description fetch is handled inside jobspy when supported.
        return super().search(queries)


__all__ = ["LinkedInSearchSource"]
