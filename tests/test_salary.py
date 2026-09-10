"""Salary normalization and minimum-salary matching."""

from __future__ import annotations

from pathlib import Path

from core.config import (
    AppConfig,
    EmploymentConfig,
    JobsConfig,
    LocationConfig,
    ProfileConfig,
    SettingsConfig,
    load_config,
    save_config,
)
from core.matcher import score_job
from core.models import Job
from core.salary import HOURS_PER_YEAR, meets_minimum, normalize_to_annual_gross_eur
from desktop.i18n import TRANSLATIONS, TranslationService


def test_hours_per_year_assumption():
    assert HOURS_PER_YEAR == 40 * 52 == 2080


def test_normalize_36000_annual():
    annual, reason = normalize_to_annual_gross_eur(36000, unit="annual")
    assert annual == 36000
    assert "annual" in reason.lower() or reason


def test_normalize_3000_monthly_to_36000():
    annual, reason = normalize_to_annual_gross_eur(3000, unit="monthly")
    assert annual == 36000
    assert "monthly" in reason.lower()


def test_normalize_hourly_uses_2080():
    annual, reason = normalize_to_annual_gross_eur(20, unit="hourly")
    assert annual == 20 * 2080
    assert "2080" in reason or "hourly" in reason.lower()


def test_normalize_german_yearly_text():
    annual, _ = normalize_to_annual_gross_eur(text="36.000 € brutto / Jahr")
    assert annual == 36000


def test_normalize_german_monthly_text():
    annual, _ = normalize_to_annual_gross_eur(text="3.000 EUR monatlich")
    assert annual == 36000


def test_unknown_salary_returns_none_not_reject():
    annual, reason = normalize_to_annual_gross_eur(text="nach Vereinbarung")
    assert annual is None
    assert reason
    assert meets_minimum(annual, 36000) is None


def test_ambiguous_range_returns_none_not_reject():
    annual, reason = normalize_to_annual_gross_eur(text="30.000 – 40.000 € / Jahr")
    assert annual is None
    assert "ambiguous" in reason.lower()
    assert meets_minimum(annual, 36000) is None


def test_meets_minimum_true_false_none():
    assert meets_minimum(40000, 36000) is True
    assert meets_minimum(30000, 36000) is False
    assert meets_minimum(None, 36000) is None
    assert meets_minimum(40000, None) is None


def _cfg(min_salary: float | None) -> AppConfig:
    return AppConfig(
        profile=ProfileConfig(
            location=LocationConfig(max_distance_km=50, allow_remote_germany=True),
            jobs=JobsConfig(desired_titles=["Sachbearbeiter"]),
            employment=EmploymentConfig(
                full_time=True,
                remote=True,
                hybrid=True,
                onsite=True,
                minimum_salary=min_salary,
            ),
        ),
        settings=SettingsConfig(published_within_days=30),
    )


def test_matcher_rejects_30k_when_min_36k():
    job = Job(
        title="Sachbearbeiter",
        company="Acme",
        remote_type="remote",
        description="Verwaltung",
        salary_min=30000,
        salary_text="30.000 EUR / Jahr",
        employment_type="Vollzeit",
    )
    result = score_job(job, _cfg(36000))
    assert result.excluded is True
    assert "salary" in (result.exclude_reason or "").lower() or "minimum" in (
        result.exclude_reason or ""
    ).lower()


def test_matcher_accepts_40k_when_min_36k():
    job = Job(
        title="Sachbearbeiter",
        company="Acme",
        remote_type="remote",
        description="Verwaltung",
        salary_min=40000,
        salary_text="40.000 EUR / Jahr",
        employment_type="Vollzeit",
    )
    result = score_job(job, _cfg(36000))
    assert result.excluded is False
    assert any("salary" in r.lower() or "minimum" in r.lower() for r in result.match_reasons)


def test_matcher_unknown_salary_does_not_exclude():
    job = Job(
        title="Sachbearbeiter",
        company="Acme",
        remote_type="remote",
        description="Verwaltung",
        salary_text="nach Vereinbarung",
        employment_type="Vollzeit",
    )
    result = score_job(job, _cfg(36000))
    assert result.excluded is False


def test_matcher_ambiguous_salary_does_not_exclude():
    job = Job(
        title="Sachbearbeiter",
        company="Acme",
        remote_type="remote",
        description="Verwaltung",
        salary_text="30k-45k yearly",
        employment_type="Vollzeit",
    )
    result = score_job(job, _cfg(36000))
    assert result.excluded is False


def test_profile_min_salary_labels_de_en():
    assert "Mindestgehalt" in TRANSLATIONS["de"]["profile.min_salary"]
    assert "Minimum salary" in TRANSLATIONS["en"]["profile.min_salary"]
    de = TranslationService("de")
    en = TranslationService("en")
    assert "Mindestgehalt" in de.t("profile.min_salary")
    assert "Minimum salary" in en.t("profile.min_salary")


def test_minimum_salary_persists_via_save_load(tmp_path: Path):
    cfg = load_config(root=tmp_path, strip_placeholders=True)
    cfg.profile.employment.minimum_salary = 42000.0
    profile = tmp_path / "profile.yaml"
    application = tmp_path / "application_profile.yaml"
    settings = tmp_path / "settings.yaml"
    save_config(
        cfg,
        profile_path=profile,
        application_path=application,
        settings_path=settings,
    )
    loaded = load_config(
        profile_path=profile,
        application_path=application,
        settings_path=settings,
        root=tmp_path,
    )
    assert loaded.profile.employment.minimum_salary == 42000.0
