"""SearchAdapter interface and health_check smoke tests."""

from search.base import JobSource, SearchAdapter
from search.bundesagentur import BundesagenturSource
from search.company_sites import CompanySitesSource
from search.indeed import IndeedSource


def test_search_adapter_alias():
    assert SearchAdapter is JobSource


def test_default_health_check_ok():
    ok, msg = CompanySitesSource().health_check()
    assert ok is True
    assert msg == "ok"


def test_indeed_health_check_reports_deps():
    ok, msg = IndeedSource().health_check()
    assert isinstance(ok, bool)
    assert isinstance(msg, str)
    assert msg


def test_bundesagentur_health_check_returns_tuple():
    ok, msg = BundesagenturSource().health_check()
    assert isinstance(ok, bool)
    assert isinstance(msg, str)
