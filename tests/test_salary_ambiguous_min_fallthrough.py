"""Regression: salary ranges must not hard-exclude via the low end alone.

Entire bands below the minimum may hard-exclude via the range ceiling; straddling
or above-minimum ceilings stay soft (no hard reject from the low end alone).
"""

from __future__ import annotations

from core.config import AppConfig, EmploymentConfig, SearchPreferences
from core.matcher import score_job
from core.models import Job
from core.salary import job_annual_salary, normalize_to_annual_gross_eur
from search.indeed import IndeedSource


def test_range_uses_ceiling_not_low_end_alone():
    annual, reason = normalize_to_annual_gross_eur(
        value=40000,
        text="40.000 – 50.000 € brutto/Jahr",
    )
    assert annual == 50000
    assert "ceiling" in reason


def test_job_annual_salary_range_text_uses_ceiling():
    job = Job(
        id="1",
        source="indeed",
        title="Sachbearbeiter",
        company="ACME",
        salary_min=40000,
        salary_max=50000,
        salary_text="40000-50000 EUR",
    )
    annual, reason = job_annual_salary(job)
    assert annual == 50000
    assert "ceiling" in reason


def test_matcher_does_not_exclude_straddling_range():
    cfg = AppConfig()
    cfg.profile = SearchPreferences(
        employment=EmploymentConfig(minimum_salary=45000),
    )
    job = Job(
        id="1",
        source="indeed",
        title="Sachbearbeiter",
        company="ACME",
        city="Berlin",
        description="Vollzeit",
        salary_min=40000,
        salary_max=50000,
        salary_text="40.000 – 50.000 €",
        url="https://example.com/job/1",
        distance_km=5,
        remote_type="onsite",
    )
    result = score_job(job, cfg)
    assert result.excluded is False
    assert result.score > 0


def test_matcher_excludes_range_entirely_below_minimum():
    cfg = AppConfig()
    cfg.profile = SearchPreferences(
        employment=EmploymentConfig(minimum_salary=45000),
    )
    job = Job(
        id="2",
        source="indeed",
        title="Sachbearbeiter",
        company="ACME",
        city="Berlin",
        description="Vollzeit",
        salary_min=20000,
        salary_max=28000,
        salary_text="20000 – 28000 EUR / Jahr",
        url="https://example.com/job/2",
        distance_km=5,
        remote_type="onsite",
    )
    result = score_job(job, cfg)
    assert result.excluded is True
    assert "below minimum" in (result.exclude_reason or "").lower()


def test_indeed_normalize_encodes_yearly_interval():
    src = IndeedSource()
    job = src.normalize(
        {
            "title": "Sachbearbeiter",
            "company": "ACME",
            "location": "Berlin, Deutschland",
            "job_url": "https://example.com/job/2",
            "description": "Büro",
            "id": "abc",
            "min_amount": 45000,
            "max_amount": 50000,
            "interval": "yearly",
            "currency": "EUR",
        }
    )
    assert job is not None
    assert "/year" in (job.salary_text or "")
    annual, reason = job_annual_salary(job)
    # Yearly range resolves via ceiling (high end), not the low end alone.
    assert annual == 50000
    assert "ceiling" in reason


def test_indeed_normalize_single_hourly_amount():
    src = IndeedSource()
    job = src.normalize(
        {
            "title": "Aushilfe",
            "company": "ACME",
            "location": "Hamburg",
            "job_url": "https://example.com/job/3",
            "description": "Minijob",
            "id": "h1",
            "min_amount": 15,
            "interval": "hourly",
            "currency": "EUR",
        }
    )
    assert job is not None
    assert "/hour" in (job.salary_text or "")
    annual, reason = job_annual_salary(job)
    assert annual == 15 * 2080
    assert "hourly" in reason or "hour" in reason
