"""Configuration loading for Jobhuntsaver."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return data


@dataclass
class LocationConfig:
    home_address: str = "Musterstraße 1, 12345 Musterstadt, Germany"
    max_distance_km: float = 20.0
    allow_remote_germany: bool = True
    allow_hybrid: bool = True
    country: str = "DE"
    home_latitude: float | None = None
    home_longitude: float | None = None


@dataclass
class JobsConfig:
    desired_titles: list[str] = field(default_factory=list)
    alternative_titles: list[str] = field(default_factory=list)
    unwanted_titles: list[str] = field(default_factory=list)
    desired_industries: list[str] = field(default_factory=list)
    excluded_industries: list[str] = field(default_factory=list)


@dataclass
class EmploymentConfig:
    full_time: bool = True
    part_time: bool = False
    remote: bool = True
    hybrid: bool = True
    onsite: bool = True
    minimum_salary: float | None = None


@dataclass
class QualificationsConfig:
    education: list[str] = field(default_factory=list)
    work_experience: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    software: list[str] = field(default_factory=list)
    driving_license: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)


@dataclass
class FiltersConfig:
    desired_keywords: list[str] = field(default_factory=list)
    exclusion_keywords: list[str] = field(default_factory=list)
    preferred_companies: list[str] = field(default_factory=list)
    excluded_companies: list[str] = field(default_factory=list)


@dataclass
class ProfileConfig:
    location: LocationConfig = field(default_factory=LocationConfig)
    jobs: JobsConfig = field(default_factory=JobsConfig)
    employment: EmploymentConfig = field(default_factory=EmploymentConfig)
    qualifications: QualificationsConfig = field(default_factory=QualificationsConfig)
    filters: FiltersConfig = field(default_factory=FiltersConfig)


@dataclass
class ApplicationProfile:
    first_name: str = ""
    last_name: str = ""
    address: str = ""
    email: str = ""
    phone: str = ""
    date_of_birth: str = ""
    driving_license: str = ""
    work_authorization: str = ""
    notice_period: str = ""
    earliest_start_date: str = ""
    salary_expectation: str = ""
    current_employment: str = ""
    education: str = ""
    work_experience: str = ""
    languages: str = ""
    willingness_to_travel: str = ""
    willingness_to_relocate: str = ""
    remote_preference: str = ""
    linkedin_url: str = ""
    portfolio_url: str = ""
    cv_path: str = ""
    answers: dict[str, str] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def phone_full(self) -> str:
        return self.phone


@dataclass
class SettingsConfig:
    mode: str = "search_only"
    dry_run: bool = True
    minimum_match_for_auto_apply: int = 75
    minimum_match_for_dashboard: int = 60
    max_applications_per_run: int = 10
    max_applications_per_day: int = 25
    max_failed_applications_per_run: int = 5
    delay_between_applications_seconds: int = 30
    headless: bool = True
    published_within_days: int = 14
    hide_already_applied: bool = True
    hide_duplicates: bool = True
    database_path: str = "data/jobs.db"
    logs_dir: str = "logs"
    browser_profile_dir: str = "private/browser_profile"
    enabled_sources: list[str] = field(
        default_factory=lambda: ["bundesagentur", "indeed"]
    )
    geocoder: str = "nominatim"
    cover_letter_template: str = "templates/cover_letter.txt"
    exclude_on_missing_mandatory: bool = False


@dataclass
class AppConfig:
    profile: ProfileConfig = field(default_factory=ProfileConfig)
    application: ApplicationProfile = field(default_factory=ApplicationProfile)
    settings: SettingsConfig = field(default_factory=SettingsConfig)
    root: Path = field(default_factory=lambda: ROOT)

    @property
    def db_path(self) -> Path:
        path = Path(self.settings.database_path)
        if not path.is_absolute():
            path = self.root / path
        return path


def _merge_dataclass(cls, data: dict[str, Any]):
    if not data:
        return cls()
    fields = getattr(cls, "__dataclass_fields__", {})
    kwargs = {}
    for name, f in fields.items():
        if name not in data:
            continue
        value = data[name]
        # With from __future__ import annotations, f.type may be a string.
        nested = f.type
        if isinstance(nested, str):
            nested = globals().get(nested, nested)
        if isinstance(value, dict) and hasattr(nested, "__dataclass_fields__"):
            kwargs[name] = _merge_dataclass(nested, value)
        else:
            kwargs[name] = value
    return cls(**kwargs)


def load_config(
    profile_path: Path | None = None,
    application_path: Path | None = None,
    settings_path: Path | None = None,
) -> AppConfig:
    load_dotenv(ROOT / ".env")
    profile_path = profile_path or CONFIG_DIR / "profile.yaml"
    application_path = application_path or CONFIG_DIR / "application_profile.yaml"
    settings_path = settings_path or CONFIG_DIR / "settings.yaml"

    # Prefer real files; fall back to examples for first run
    if not profile_path.exists():
        profile_path = CONFIG_DIR / "profile.yaml.example"
    if not application_path.exists():
        application_path = CONFIG_DIR / "application_profile.yaml.example"
    if not settings_path.exists():
        settings_path = CONFIG_DIR / "settings.yaml.example"

    profile_raw = _load_yaml(profile_path)
    application_raw = _load_yaml(application_path)
    settings_raw = _load_yaml(settings_path)

    location = _merge_dataclass(LocationConfig, profile_raw.get("location", {}))
    jobs = _merge_dataclass(JobsConfig, profile_raw.get("jobs", {}))
    employment = _merge_dataclass(EmploymentConfig, profile_raw.get("employment", {}))
    qualifications = _merge_dataclass(
        QualificationsConfig, profile_raw.get("qualifications", {})
    )
    filters = _merge_dataclass(FiltersConfig, profile_raw.get("filters", {}))
    profile = ProfileConfig(
        location=location,
        jobs=jobs,
        employment=employment,
        qualifications=qualifications,
        filters=filters,
    )
    application = _merge_dataclass(ApplicationProfile, application_raw)
    settings = _merge_dataclass(SettingsConfig, settings_raw)

    # Env overrides for secrets only — never required for search_only
    if os.getenv("CV_PATH"):
        application.cv_path = os.environ["CV_PATH"]

    return AppConfig(profile=profile, application=application, settings=settings)
