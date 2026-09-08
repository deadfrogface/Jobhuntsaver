"""Core domain models for Jobhuntsaver."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class JobStatus(str, Enum):
    NEW = "new"
    INTERESTING = "interesting"
    IGNORED = "ignored"
    QUEUED = "queued"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    CAPTCHA = "captcha"
    CLOSED = "closed"


class RemoteType(str, Enum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"
    UNKNOWN = "unknown"


class OperatingMode(str, Enum):
    SEARCH_ONLY = "search_only"
    REVIEW_BEFORE_SUBMIT = "review_before_submit"
    FULLY_AUTOMATIC = "fully_automatic"


@dataclass
class Job:
    id: str = ""
    source: str = ""
    source_job_id: str = ""
    title: str = ""
    company: str = ""
    description: str = ""
    city: str = ""
    postal_code: str = ""
    address: str = ""
    latitude: float | None = None
    longitude: float | None = None
    distance_km: float | None = None
    remote_type: str = RemoteType.UNKNOWN.value
    employment_type: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    salary_text: str = ""
    published_at: str = ""
    discovered_at: str = field(default_factory=utc_now_iso)
    url: str = ""
    application_url: str = ""
    ats_type: str = "unknown"
    match_score: int = 0
    match_reasons: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    status: str = JobStatus.NEW.value
    duplicate_of: str | None = None
    alt_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        for list_field in ("match_reasons", "rejection_reasons", "alt_sources"):
            if list_field in filtered and isinstance(filtered[list_field], str):
                import json

                try:
                    filtered[list_field] = json.loads(filtered[list_field])
                except json.JSONDecodeError:
                    filtered[list_field] = []
        return cls(**filtered)


@dataclass
class ApplicationRecord:
    id: str = ""
    job_id: str = ""
    company: str = ""
    position: str = ""
    application_date: str = field(default_factory=utc_now_iso)
    platform: str = ""
    status: str = JobStatus.APPLYING.value
    cv_used: str = ""
    cover_letter_used: str = ""
    result: str = ""
    error_message: str = ""


@dataclass
class MatchResult:
    score: int
    match_reasons: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    excluded: bool = False
    exclude_reason: str | None = None
