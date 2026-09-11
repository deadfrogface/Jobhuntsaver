"""Regression: ambiguous salary ranges must not hard-exclude via salary_min fallthrough."""

from __future__ import annotations

from core.config import AppConfig, EmploymentConfig, SearchPreferences
from core.matcher import score_job
from core.models import Job
from core.salary import job_annual_salary, normalize_to_annual_gross_eur
from search.indeed import IndeedSource


def test_ambiguous_range_with_salary_min_stays_unknown():
    annual, reason = normalize_to_annual_gross_eur(
        value=40000,
        text="40.000 – 50.000 € brutto/Jahr",
    )
    assert annual is None
    assert "ambiguous" in reason


def test_job_annual_salary_ignores_min_when_text_is_range():
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
    assert annual is None
    assert "ambiguous" in reason


def test_matcher_does_not_exclude_ambiguous_range_with_salary_min():
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
    )
    result = score_job(job, cfg)
    assert result.excluded is False
    assert result.score > 0


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
    # Range remains ambiguous even with yearly unit — no hard reject.
    assert annual is None
    assert "ambiguous" in reason


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
