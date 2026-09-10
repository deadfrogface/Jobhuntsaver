"""Offline source contracts: placeholders and garbage HTTP must not crash."""

from __future__ import annotations

from core.source_health import SourceHealthStatus
from search.base import SearchQuery
from search.company_sites import CompanySitesSource
from search.stepstone import StepstoneSource
from search.xing import XingSource


def test_company_sites_empty_placeholder():
    src = CompanySitesSource()
    assert src.search([SearchQuery(keyword="test")]) == []
    status = SourceHealthStatus.from_outcome(
        jobs_found=0, source_id="company_sites", placeholder=True
    )
    assert status == SourceHealthStatus.PLACEHOLDER
    assert status != SourceHealthStatus.OK_EMPTY
    assert status != SourceHealthStatus.OK_WITH_RESULTS


def test_stepstone_garbage_http_does_not_crash(monkeypatch):
    class _Resp:
        text = "<<<not-html-or-json>>>"
        status_code = 200

        def raise_for_status(self):
            return None

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **k):
            return _Resp()

    monkeypatch.setattr("search.stepstone.httpx.Client", _Client)
    src = StepstoneSource()
    jobs = src.search([SearchQuery(keyword="Sachbearbeiter", location="Berlin")])
    assert isinstance(jobs, list)


def test_xing_garbage_http_does_not_crash(monkeypatch):
    class _Resp:
        text = "{not valid json{{{{"
        status_code = 200

        def raise_for_status(self):
            return None

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **k):
            return _Resp()

    monkeypatch.setattr("search.xing.httpx.Client", _Client)
    src = XingSource()
    jobs = src.search([SearchQuery(keyword="Sachbearbeiter", location="Berlin")])
    assert isinstance(jobs, list)


def test_source_health_status_distinctions():
    assert SourceHealthStatus.from_outcome(jobs_found=3) == SourceHealthStatus.OK_WITH_RESULTS
    assert SourceHealthStatus.from_outcome(jobs_found=0, source_id="indeed") == SourceHealthStatus.OK_EMPTY
    assert (
        SourceHealthStatus.from_outcome(jobs_found=0, source_id="company_sites")
        == SourceHealthStatus.PLACEHOLDER
    )
    assert (
        SourceHealthStatus.from_outcome(jobs_found=0, error="Timeout after 120s")
        == SourceHealthStatus.TIMEOUT
    )
    assert (
        SourceHealthStatus.from_outcome(jobs_found=0, error="HTTP 403 blocked")
        == SourceHealthStatus.BLOCKED
        or SourceHealthStatus.from_outcome(jobs_found=0, error="HTTP 403 blocked")
        == SourceHealthStatus.AUTH_REQUIRED
    )
    assert SourceHealthStatus.OK_EMPTY != SourceHealthStatus.PLACEHOLDER
    assert SourceHealthStatus.TIMEOUT != SourceHealthStatus.ERROR
