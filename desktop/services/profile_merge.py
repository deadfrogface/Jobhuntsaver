"""Merge CV-extracted qualifications into an existing profile without blind duplicates."""

from __future__ import annotations

from dataclasses import replace
from typing import Literal

from core.config import (
    CertificateEntry,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
    QualificationsConfig,
)

Action = Literal["add", "update", "keep", "ignore"]


def _merge_list_str(existing: list[str], incoming: list[str], action: Action) -> list[str]:
    if action == "ignore" or action == "keep":
        return list(existing)
    if action == "update":
        # Replace empty profile with incoming; otherwise union
        if not existing:
            return list(dict.fromkeys(incoming))
    seen = {e.lower() for e in existing}
    out = list(existing)
    for item in incoming:
        if item.lower() not in seen:
            out.append(item)
            seen.add(item.lower())
    return out


def _merge_by_key(existing: list, incoming: list, action: Action) -> list:
    if action == "ignore":
        return list(existing)
    if action == "keep":
        return list(existing)
    by_key = {item.normalized_key(): item for item in existing if item.normalized_key()}
    order = [item.normalized_key() for item in existing if item.normalized_key()]
    for item in incoming:
        key = item.normalized_key()
        if not key:
            continue
        if key in by_key:
            if action == "update":
                by_key[key] = item
            # add: skip duplicate
        else:
            by_key[key] = item
            order.append(key)
    # Preserve existing order, append new
    return [by_key[k] for k in order if k in by_key]


def merge_qualifications(
    existing: QualificationsConfig,
    incoming: QualificationsConfig,
    *,
    languages: Action = "add",
    education: Action = "add",
    work_experience: Action = "add",
    certificates: Action = "add",
    skills: Action = "add",
    software: Action = "add",
    driving_license: Action = "add",
) -> QualificationsConfig:
    return QualificationsConfig(
        languages=_merge_by_key(existing.languages, incoming.languages, languages),
        education=_merge_by_key(existing.education, incoming.education, education),
        work_experience=_merge_by_key(
            existing.work_experience, incoming.work_experience, work_experience
        ),
        certificates=_merge_by_key(existing.certificates, incoming.certificates, certificates),
        skills=_merge_list_str(existing.skills, incoming.skills, skills),
        software=_merge_list_str(existing.software, incoming.software, software),
        driving_license=_merge_list_str(
            existing.driving_license, incoming.driving_license, driving_license
        ),
    )


def summarize_incoming(q: QualificationsConfig) -> dict[str, list[str]]:
    return {
        "languages": q.language_labels(),
        "education": q.education_labels(),
        "work_experience": q.experience_labels(),
        "certificates": q.certificate_labels(),
        "skills": list(q.skills),
        "software": list(q.software),
        "driving_license": list(q.driving_license),
    }
