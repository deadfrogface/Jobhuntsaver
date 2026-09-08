"""Configuration loading for Jobhuntsaver."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"

# Exact placeholder sets from older example configs — never treat as real data.
EXAMPLE_SKILL_SET = {"ms office", "kommunikation"}
EXAMPLE_SOFTWARE_SET = {"excel", "outlook"}
EXAMPLE_LANGUAGE_SET = {"deutsch (c1)", "englisch (b1)"}
EXAMPLE_KEYWORD_SET = {"kunden", "verwaltung"}


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
    home_address: str = ""
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
class LanguageEntry:
    language: str = ""
    level: str = ""
    source: str = ""  # manual | cv | default | "" (legacy → replaceable)

    def label(self) -> str:
        if self.language and self.level:
            return f"{self.language} | {self.level}"
        return self.language or self.level

    def normalized_key(self) -> str:
        return self.language.strip().lower()


@dataclass
class EducationEntry:
    qualification: str = ""
    institution: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    completion_date: str = ""
    source: str = ""

    def label(self) -> str:
        parts = [self.qualification, self.institution, self.completion_date or self.end_date]
        return " – ".join(p for p in parts if p)

    def normalized_key(self) -> str:
        return f"{self.qualification}|{self.institution}".strip().lower()

    def search_tokens(self) -> list[str]:
        return [t for t in (self.qualification, self.institution, self.location) if t]


@dataclass
class ExperienceEntry:
    title: str = ""
    company: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    responsibilities: list[str] = field(default_factory=list)
    source: str = ""

    def label(self) -> str:
        period = " – ".join(p for p in (self.start_date, self.end_date) if p)
        head = " @ ".join(p for p in (self.title, self.company) if p)
        return f"{head} ({period})" if period else head

    def normalized_key(self) -> str:
        return f"{self.title}|{self.company}|{self.start_date}".strip().lower()

    def search_tokens(self) -> list[str]:
        tokens = [self.title, self.company, self.location]
        tokens.extend(self.responsibilities)
        return [t for t in tokens if t]


@dataclass
class CertificateEntry:
    name: str = ""
    issuer: str = ""
    date: str = ""
    source: str = ""

    def label(self) -> str:
        parts = [self.name, self.issuer, self.date]
        return " – ".join(p for p in parts if p)

    def normalized_key(self) -> str:
        return self.name.strip().lower()


@dataclass
class SourcedText:
    value: str = ""
    source: str = ""

    def normalized_key(self) -> str:
        return self.value.strip().lower()

    def label(self) -> str:
        return self.value


def _sourced_value(item: Any) -> str:
    if isinstance(item, SourcedText):
        return item.value.strip()
    return str(item or "").strip()


@dataclass
class QualificationsConfig:
    education: list[EducationEntry] = field(default_factory=list)
    work_experience: list[ExperienceEntry] = field(default_factory=list)
    skills: list[SourcedText] = field(default_factory=list)
    software: list[SourcedText] = field(default_factory=list)
    driving_license: list[SourcedText] = field(default_factory=list)
    languages: list[LanguageEntry] = field(default_factory=list)
    certificates: list[CertificateEntry] = field(default_factory=list)

    def skill_values(self) -> list[str]:
        return [_sourced_value(s) for s in self.skills if _sourced_value(s)]

    def software_values(self) -> list[str]:
        return [_sourced_value(s) for s in self.software if _sourced_value(s)]

    def driving_values(self) -> list[str]:
        return [_sourced_value(s) for s in self.driving_license if _sourced_value(s)]

    def language_labels(self) -> list[str]:
        return [lang.label() for lang in self.languages if lang.language]

    def education_labels(self) -> list[str]:
        return [e.label() for e in self.education if e.qualification or e.institution]

    def experience_labels(self) -> list[str]:
        return [e.label() for e in self.work_experience if e.title or e.company]

    def certificate_labels(self) -> list[str]:
        return [c.label() for c in self.certificates if c.name]

    def all_match_tokens(self) -> list[str]:
        """Flattened tokens for job matching (no invented values)."""
        tokens: list[str] = []
        tokens.extend(self.skill_values())
        tokens.extend(self.software_values())
        tokens.extend(self.driving_values())
        tokens.extend(self.language_labels())
        for edu in self.education:
            tokens.extend(edu.search_tokens())
        for exp in self.work_experience:
            tokens.extend(exp.search_tokens())
        for cert in self.certificates:
            if cert.name:
                tokens.append(cert.name)
        return [t for t in tokens if t and str(t).strip()]


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
    street: str = ""
    postal_code: str = ""
    city: str = ""
    country: str = "DE"
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
    # Track origin of personal fields: manual | cv | default
    field_origins: dict[str, str] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def phone_full(self) -> str:
        return self.phone

    def sync_address(self) -> None:
        """Compose legacy `address` from structured fields when present."""
        parts = [
            p.strip()
            for p in (
                self.street,
                f"{self.postal_code} {self.city}".strip(),
                self.country,
            )
            if p and str(p).strip()
        ]
        if parts:
            self.address = ", ".join(parts)


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
    automatic_cover_letters: bool = True
    automatic_submission: bool = False
    automation_paused: bool = False
    run_automatically: bool = False
    schedule_mode: str = "every_x_hours"
    schedule_interval_hours: int = 6
    schedule_times: list[str] = field(default_factory=lambda: ["08:00"])
    # Desktop UX
    theme: str = "system"  # system | light | dark
    language: str = "de"  # de | en
    start_with_windows: bool = False
    minimize_to_tray: bool = True


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
    field_map = getattr(cls, "__dataclass_fields__", {})
    kwargs = {}
    for name, f in field_map.items():
        if name not in data:
            continue
        value = data[name]
        nested = f.type
        if isinstance(nested, str):
            nested = globals().get(nested, nested)
        if isinstance(value, dict) and hasattr(nested, "__dataclass_fields__"):
            kwargs[name] = _merge_dataclass(nested, value)
        else:
            kwargs[name] = value
    return cls(**kwargs)


def _parse_language(value: Any) -> LanguageEntry | None:
    if isinstance(value, LanguageEntry):
        return value
    if isinstance(value, dict):
        lang = str(value.get("language") or "").strip()
        level = str(value.get("level") or "").strip()
        source = str(value.get("source") or "").strip()
        if not lang and not level:
            return None
        return LanguageEntry(language=lang, level=level, source=source)
    if isinstance(value, str) and value.strip():
        text = value.strip()
        m = re.match(
            r"^(?P<lang>.+?)\s*(?:\||–|-|—)?\s*\(?(?P<level>[ABC][12]|Muttersprache|native)\)?\s*$",
            text,
            re.IGNORECASE,
        )
        if m:
            return LanguageEntry(
                language=m.group("lang").strip(" -–—|()"),
                level=m.group("level").strip(),
            )
        parts = re.split(r"\s*[|–—-]\s*", text, maxsplit=1)
        if len(parts) == 2 and re.fullmatch(
            r"[ABC][12]|Muttersprache|native", parts[1], re.I
        ):
            return LanguageEntry(language=parts[0].strip(), level=parts[1].strip())
        return LanguageEntry(language=text, level="")
    return None


def _parse_education(value: Any) -> EducationEntry | None:
    if isinstance(value, EducationEntry):
        return value
    if isinstance(value, dict):
        entry = EducationEntry(
            qualification=str(value.get("qualification") or "").strip(),
            institution=str(value.get("institution") or "").strip(),
            location=str(value.get("location") or "").strip(),
            start_date=str(value.get("start_date") or "").strip(),
            end_date=str(value.get("end_date") or "").strip(),
            completion_date=str(value.get("completion_date") or "").strip(),
            source=str(value.get("source") or "").strip(),
        )
        return entry if entry.qualification or entry.institution else None
    if isinstance(value, str) and value.strip():
        return EducationEntry(qualification=value.strip())
    return None


def _parse_experience(value: Any) -> ExperienceEntry | None:
    if isinstance(value, ExperienceEntry):
        return value
    if isinstance(value, dict):
        responsibilities = value.get("responsibilities") or []
        if isinstance(responsibilities, str):
            responsibilities = [responsibilities]
        entry = ExperienceEntry(
            title=str(value.get("title") or "").strip(),
            company=str(value.get("company") or "").strip(),
            location=str(value.get("location") or "").strip(),
            start_date=str(value.get("start_date") or "").strip(),
            end_date=str(value.get("end_date") or "").strip(),
            responsibilities=[str(r).strip() for r in responsibilities if str(r).strip()],
            source=str(value.get("source") or "").strip(),
        )
        return entry if entry.title or entry.company else None
    if isinstance(value, str) and value.strip():
        return ExperienceEntry(title=value.strip())
    return None


def _parse_certificate(value: Any) -> CertificateEntry | None:
    if isinstance(value, CertificateEntry):
        return value
    if isinstance(value, dict):
        entry = CertificateEntry(
            name=str(value.get("name") or "").strip(),
            issuer=str(value.get("issuer") or "").strip(),
            date=str(value.get("date") or "").strip(),
            source=str(value.get("source") or "").strip(),
        )
        return entry if entry.name else None
    if isinstance(value, str) and value.strip():
        return CertificateEntry(name=value.strip())
    return None


def _parse_sourced_text(value: Any) -> SourcedText | None:
    if isinstance(value, SourcedText):
        return value if value.value.strip() else None
    if isinstance(value, dict):
        text = str(value.get("value") or value.get("text") or "").strip()
        source = str(value.get("source") or "").strip()
        return SourcedText(value=text, source=source) if text else None
    if isinstance(value, str) and value.strip():
        # Bare strings from older YAML: replaceable until user edits (manual)
        return SourcedText(value=value.strip(), source="")
    return None


def parse_qualifications(raw: dict[str, Any] | None) -> QualificationsConfig:
    raw = raw or {}
    languages = []
    for item in raw.get("languages") or []:
        parsed = _parse_language(item)
        if parsed:
            languages.append(parsed)
    education = []
    for item in raw.get("education") or []:
        parsed = _parse_education(item)
        if parsed:
            education.append(parsed)
    experience = []
    for item in raw.get("work_experience") or []:
        parsed = _parse_experience(item)
        if parsed:
            experience.append(parsed)
    certificates = []
    for item in raw.get("certificates") or []:
        parsed = _parse_certificate(item)
        if parsed:
            certificates.append(parsed)

    def _list_sourced(key: str) -> list[SourcedText]:
        out: list[SourcedText] = []
        for item in raw.get(key) or []:
            parsed = _parse_sourced_text(item)
            if parsed:
                out.append(parsed)
        return out

    return QualificationsConfig(
        education=education,
        work_experience=experience,
        skills=_list_sourced("skills"),
        software=_list_sourced("software"),
        driving_license=_list_sourced("driving_license"),
        languages=languages,
        certificates=certificates,
    )



def strip_example_placeholders(profile: ProfileConfig) -> ProfileConfig:
    """Remove known demo qualification sets so they never influence matching."""
    q = profile.qualifications
    skill_set = {v.lower() for v in q.skill_values()}
    software_set = {v.lower() for v in q.software_values()}
    lang_set = {lang.label().lower() for lang in q.languages} | {
        f"{lang.language} ({lang.level})".lower() for lang in q.languages if lang.level
    }
    keyword_set = {k.lower() for k in profile.filters.desired_keywords}

    if skill_set and skill_set <= EXAMPLE_SKILL_SET:
        q.skills = []
    if software_set and software_set <= EXAMPLE_SOFTWARE_SET:
        q.software = []
    if lang_set and lang_set <= EXAMPLE_LANGUAGE_SET | {"deutsch | c1", "englisch | b1"}:
        q.languages = []
    if keyword_set and keyword_set <= EXAMPLE_KEYWORD_SET:
        profile.filters.desired_keywords = []
    return profile


# Demo application fingerprint from older examples — never treat as real user data.
EXAMPLE_APPLICATION_MARKERS = {
    "first_name": "max",
    "last_name": "mustermann",
    "email": "max.mustermann@example.com",
}


def strip_example_application(application: ApplicationProfile) -> ApplicationProfile:
    """Clear Mustermann-style demo personal data from production configs."""
    fn = (application.first_name or "").strip().lower()
    ln = (application.last_name or "").strip().lower()
    em = (application.email or "").strip().lower()
    is_demo = (
        fn == EXAMPLE_APPLICATION_MARKERS["first_name"]
        and ln == EXAMPLE_APPLICATION_MARKERS["last_name"]
    ) or em == EXAMPLE_APPLICATION_MARKERS["email"]
    if not is_demo:
        return application
    for name in (
        "first_name",
        "last_name",
        "address",
        "street",
        "postal_code",
        "city",
        "email",
        "phone",
        "date_of_birth",
        "driving_license",
        "work_authorization",
        "notice_period",
        "earliest_start_date",
        "salary_expectation",
        "current_employment",
        "education",
        "work_experience",
        "languages",
        "willingness_to_travel",
        "willingness_to_relocate",
        "remote_preference",
        "linkedin_url",
        "portfolio_url",
        "cv_path",
    ):
        setattr(application, name, "")
    application.country = "DE"
    application.answers = {}
    application.field_origins = {}
    return application


def _dataclass_to_dict(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _dataclass_to_dict(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, list):
        return [_dataclass_to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


def _dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def save_config(
    config: AppConfig,
    *,
    profile_path: Path | None = None,
    application_path: Path | None = None,
    settings_path: Path | None = None,
) -> None:
    """Persist GUI-editable configuration to YAML files."""
    profile_path = profile_path or CONFIG_DIR / "profile.yaml"
    application_path = application_path or CONFIG_DIR / "application_profile.yaml"
    settings_path = settings_path or CONFIG_DIR / "settings.yaml"

    config.application.sync_address()
    profile_data = {
        "location": _dataclass_to_dict(config.profile.location),
        "jobs": _dataclass_to_dict(config.profile.jobs),
        "employment": _dataclass_to_dict(config.profile.employment),
        "qualifications": _dataclass_to_dict(config.profile.qualifications),
        "filters": _dataclass_to_dict(config.profile.filters),
    }
    application_data = _dataclass_to_dict(config.application)
    settings_data = _dataclass_to_dict(config.settings)
    _dump_yaml(profile_path, profile_data)
    _dump_yaml(application_path, application_data)
    _dump_yaml(settings_path, settings_data)


def load_config(
    profile_path: Path | None = None,
    application_path: Path | None = None,
    settings_path: Path | None = None,
    root: Path | None = None,
    *,
    strip_placeholders: bool = True,
) -> AppConfig:
    root = root or ROOT
    load_dotenv(root / ".env")
    load_dotenv(ROOT / ".env")
    example_dir = CONFIG_DIR
    profile_path = profile_path or (root / "config" / "profile.yaml")
    application_path = application_path or (root / "config" / "application_profile.yaml")
    settings_path = settings_path or (root / "config" / "settings.yaml")

    if not profile_path.exists():
        profile_path = example_dir / "profile.yaml.example"
    if not application_path.exists():
        application_path = example_dir / "application_profile.yaml.example"
    if not settings_path.exists():
        settings_path = example_dir / "settings.yaml.example"

    profile_raw = _load_yaml(profile_path)
    application_raw = _load_yaml(application_path)
    settings_raw = _load_yaml(settings_path)

    location = _merge_dataclass(LocationConfig, profile_raw.get("location", {}))
    jobs = _merge_dataclass(JobsConfig, profile_raw.get("jobs", {}))
    employment = _merge_dataclass(EmploymentConfig, profile_raw.get("employment", {}))
    qualifications = parse_qualifications(profile_raw.get("qualifications", {}))
    filters = _merge_dataclass(FiltersConfig, profile_raw.get("filters", {}))
    profile = ProfileConfig(
        location=location,
        jobs=jobs,
        employment=employment,
        qualifications=qualifications,
        filters=filters,
    )
    if strip_placeholders:
        profile = strip_example_placeholders(profile)
    application = _merge_dataclass(ApplicationProfile, application_raw)
    if strip_placeholders:
        application = strip_example_application(application)
    settings = _merge_dataclass(SettingsConfig, settings_raw)

    if os.getenv("CV_PATH"):
        application.cv_path = os.environ["CV_PATH"]

    return AppConfig(
        profile=profile,
        application=application,
        settings=settings,
        root=root,
    )
