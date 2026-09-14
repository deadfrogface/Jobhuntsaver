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


def test_soft_dedup_strips_legal_suffix_and_gender_tag():
    """Portal twins often differ by GmbH and (m/w/d) — must still collapse."""
    a = Job(
        id="1",
        source="indeed",
        title="Software Engineer (m/w/d)",
        company="Acme GmbH",
        city="Berlin",
        url="https://indeed.example/1",
    )
    b = Job(
        id="2",
        source="stepstone",
        title="Software Engineer",
        company="Acme",
        city="Berlin",
        url="https://stepstone.example/2",
    )
    assert is_likely_same_job(a, b) is True
    out = deduplicate([a, b])
    assert sum(1 for j in out if j.duplicate_of) == 1


def test_ba_beats_indeed_when_ats_type_unknown():
    """Default ats_type 'unknown' must not override source priority (BA > Indeed)."""
    ba = Job(
        id="ba-1",
        source="bundesagentur",
        title="Sachbearbeiter",
        company="ACME",
        city="Berlin",
        url="https://www.arbeitsagentur.de/jobsuche/jobdetail/123",
        ats_type="unknown",
    )
    indeed = Job(
        id="in-1",
        source="indeed",
        title="Sachbearbeiter",
        company="ACME",
        city="Berlin",
        url="https://de.indeed.com/viewjob?jk=abc",
        ats_type="unknown",
    )
    out = deduplicate([indeed, ba])
    primary = [j for j in out if not j.duplicate_of]
    assert len(primary) == 1
    assert primary[0].source == "bundesagentur"
    assert "indeed" in primary[0].alt_sources or any(
        j.duplicate_of == primary[0].id for j in out
    )
