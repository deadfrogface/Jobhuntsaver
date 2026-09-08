"""Matcher and hard-filter tests."""

from core.config import AppConfig, EmploymentConfig, FiltersConfig, JobsConfig, LocationConfig, ProfileConfig, QualificationsConfig, SettingsConfig
from core.matcher import score_job
from core.models import Job


def _config() -> AppConfig:
    return AppConfig(
        profile=ProfileConfig(
            location=LocationConfig(max_distance_km=20, allow_remote_germany=True, allow_hybrid=True),
            jobs=JobsConfig(desired_titles=["Sachbearbeiter"], unwanted_titles=["Praktikant"]),
            employment=EmploymentConfig(full_time=True, remote=True, hybrid=True, onsite=True),
            qualifications=QualificationsConfig(
                skills=["Excel", "Kommunikation"],
                languages=["Deutsch (C1)"],
                driving_license=["B"],
            ),
            filters=FiltersConfig(desired_keywords=["Verwaltung"], excluded_companies=["BadCorp"]),
        ),
        settings=SettingsConfig(published_within_days=30),
    )


def test_exclude_far_onsite():
    job = Job(title="Sachbearbeiter", company="ACME", remote_type="onsite", distance_km=35, description="Excel Verwaltung Deutsch")
    result = score_job(job, _config())
    assert result.excluded
    assert "km" in (result.exclude_reason or "")


def test_remote_no_distance_penalty():
    job = Job(
        title="Sachbearbeiter Verwaltung",
        company="ACME",
        remote_type="remote",
        distance_km=500,
        description="Excel Kommunikation Deutsch Verwaltung",
        employment_type="fulltime",
    )
    result = score_job(job, _config())
    assert not result.excluded
    assert result.score >= 60
    assert any("remote" in r.lower() for r in result.match_reasons)


def test_excluded_company():
    job = Job(title="Sachbearbeiter", company="BadCorp AG", remote_type="remote", description="x")
    result = score_job(job, _config())
    assert result.excluded


def test_nearby_score_reasons():
    job = Job(
        title="Sachbearbeiter",
        company="Good",
        remote_type="onsite",
        distance_km=7.2,
        description="Excel Verwaltung Deutsch Kommunikation",
        employment_type="Vollzeit",
    )
    result = score_job(job, _config())
    assert result.score > 50
    assert result.match_reasons
