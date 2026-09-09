"""Source timeout isolation — one hung source must not stop others."""

from __future__ import annotations

import time

from app.main import SOURCE_SEARCH_TIMEOUT_S, _search_source_with_timeout
from core.models import Job
from search.base import JobSource, SearchQuery


class _SlowSource(JobSource):
    source_id = "slow"

    def search(self, queries: list[SearchQuery]) -> list[Job]:
        time.sleep(5)
        return []


class _FastSource(JobSource):
    source_id = "fast"

    def search(self, queries: list[SearchQuery]) -> list[Job]:
        return [
            Job(
                id="f1",
                source="fast",
                source_job_id="1",
                title="Office",
                company="Acme",
            )
        ]


def test_one_source_timeout_returns_error_tuple():
    jobs, err, detail = _search_source_with_timeout(
        _SlowSource(),
        [SearchQuery(keyword="x")],
        timeout_s=0.3,
    )
    assert jobs == []
    assert err is not None
    assert "Timeout" in err


def test_fast_source_still_works_after_timeout_pattern():
    slow_jobs, slow_err, _ = _search_source_with_timeout(
        _SlowSource(), [SearchQuery(keyword="x")], timeout_s=0.2
    )
    assert slow_err
    fast_jobs, fast_err, _ = _search_source_with_timeout(
        _FastSource(), [SearchQuery(keyword="x")], timeout_s=5
    )
    assert fast_err is None
    assert len(fast_jobs) == 1
    assert SOURCE_SEARCH_TIMEOUT_S >= 30
