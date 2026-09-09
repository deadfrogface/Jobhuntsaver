"""SearchAdapter interface and health_check smoke tests."""

from search.base import JobSource, SearchAdapter
from search.bundesagentur import BundesagenturSource
from search.company_sites import CompanySitesSource
from search.indeed import IndeedSource


def test_search_adapter_alias():
    assert SearchAdapter is JobSource


def test_default_health_check_ok():
    from search.base import JobSource, SearchQuery
    from core.models import Job

    class _Dummy(JobSource):
        source_id = "dummy"

        def search(self, queries: list[SearchQuery]) -> list[Job]:
            return []

    ok, msg = _Dummy().health_check()
    assert ok is True
    assert msg == "ok"


def test_company_sites_health_check_placeholder():
    ok, msg = CompanySitesSource().health_check()
    assert ok is True
    assert "placeholder" in msg


def test_indeed_normalize_maps_row():
    src = IndeedSource()
    job = src.normalize(
        {
            "title": "Sachbearbeiter",
            "company": "Beispiel GmbH",
            "location": "Berlin, Deutschland",
            "job_url": "https://example.com/job/1",
            "description": "Büro",
            "id": "abc",
        }
    )
    assert job is not None
    assert job.title == "Sachbearbeiter"
    assert job.city == "Berlin"
    assert job.source == "indeed"


def test_bundesagentur_health_check_returns_tuple():
    ok, msg = BundesagenturSource().health_check()
    assert isinstance(ok, bool)
    assert isinstance(msg, str)
