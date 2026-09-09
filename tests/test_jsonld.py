"""Shared JobPosting JSON-LD helper tests."""

from search.jsonld import iter_job_postings, job_from_job_posting


def test_iter_job_postings_from_graph():
    payload = {
        "@graph": [
            {"@type": "JobPosting", "title": "Sachbearbeiter", "url": "https://ex.com/1"},
            {"@type": "Organization", "name": "Ignore"},
        ]
    }
    posts = iter_job_postings(payload)
    assert len(posts) == 1
    assert posts[0]["title"] == "Sachbearbeiter"


def test_job_from_job_posting_remote_and_html_description():
    job = job_from_job_posting(
        {
            "title": "Remote Support",
            "url": "https://example.com/jobs/2",
            "hiringOrganization": {"name": "Beispiel GmbH"},
            "jobLocation": {"address": {"addressLocality": "Hamburg"}},
            "description": "<p>Homeoffice möglich</p>",
            "datePosted": "2026-01-01",
        },
        source="stepstone",
    )
    assert job is not None
    assert job.source == "stepstone"
    assert job.company == "Beispiel GmbH"
    assert job.city == "Hamburg"
    assert "Homeoffice" in job.description
    assert job.remote_type in {"remote", "hybrid"}


def test_job_from_job_posting_min_title_len():
    assert job_from_job_posting({"title": "AB", "url": "u"}, source="xing", min_title_len=4) is None
