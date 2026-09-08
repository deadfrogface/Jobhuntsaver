"""Duplicate detection tests."""

from core.deduplicator import deduplicate, fingerprint, is_likely_same_job, make_job_id
from core.models import Job


def test_make_job_id_stable():
    a = make_job_id("bundesagentur", "123", "https://x")
    b = make_job_id("bundesagentur", "123", "https://x")
    assert a == b


def test_deduplicate_prefers_ats_over_portal():
    portal = Job(
        id="1",
        source="indeed",
        title="Sachbearbeiter",
        company="ACME",
        city="Musterstadt",
        url="https://indeed.example/1",
        ats_type="indeed",
    )
    ats = Job(
        id="2",
        source="company_site",
        title="Sachbearbeiter",
        company="ACME",
        city="Musterstadt",
        url="https://boards.greenhouse.io/acme/jobs/1",
        ats_type="greenhouse",
    )
    out = deduplicate([portal, ats])
    primary = [j for j in out if not j.duplicate_of]
    assert len(primary) == 1
    assert primary[0].ats_type == "greenhouse"
    assert "indeed" in primary[0].alt_sources or any(j.duplicate_of for j in out)


def test_fingerprint_and_likely_same():
    a = Job(title="Verkäufer", company="Shop GmbH", city="Düsseldorf")
    b = Job(title="Verkäufer", company="Shop GmbH", city="Düsseldorf")
    assert fingerprint(a) == fingerprint(b)
    assert is_likely_same_job(a, b)
