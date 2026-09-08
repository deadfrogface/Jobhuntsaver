"""Local job matching (0-100) without LLM APIs.

Adapted from AutoApply core/filter.py scoring ideas, extended with
distance bands, remote/hybrid, skills, languages, and reason strings.
"""

from __future__ import annotations

import re

from core.config import AppConfig
from core.hard_filter import hard_exclude
from core.models import Job, MatchResult, RemoteType


def _extract_salary_number(salary_str: str) -> int | None:
    cleaned = salary_str.replace(",", ".").replace("€", "").replace("EUR", "").strip().lower()
    numbers = re.findall(r"[\d.]+", cleaned)
    if not numbers:
        return None
    try:
        value = float(numbers[0].replace(",", "."))
    except ValueError:
        return None
    if "k" in cleaned and value < 1000:
        value *= 1000
    # Monthly heuristic for DE ads under 10k
    if value < 10000:
        value *= 12
    return int(value)


def _distance_points(distance_km: float | None, remote_type: str) -> tuple[int, str | None, str | None]:
    if remote_type == RemoteType.REMOTE.value:
        return 20, "100% remote — no distance penalty", None
    if distance_km is None:
        return 8, None, "Distance unknown"
    if distance_km <= 5:
        return 20, f"Only {distance_km} km away", None
    if distance_km <= 10:
        return 16, f"Only {distance_km} km away", None
    if distance_km <= 15:
        return 12, f"{distance_km} km away", None
    if distance_km <= 20:
        return 8, f"{distance_km} km away (acceptable)", None
    return 0, None, f"{distance_km} km exceeds commute limit"


def score_job(job: Job, config: AppConfig, already_applied: bool = False) -> MatchResult:
    exclude = hard_exclude(job, config, already_applied=already_applied)
    if exclude:
        return MatchResult(
            score=0,
            match_reasons=[],
            rejection_reasons=[exclude],
            excluded=True,
            exclude_reason=exclude,
        )

    profile = config.profile
    reasons: list[str] = []
    issues: list[str] = []
    score = 0

    title_l = job.title.lower()
    desc_l = (job.description or "").lower()
    combined = f"{title_l} {desc_l}"

    # Title match (0-30)
    title_score = 0
    all_titles = profile.jobs.desired_titles + profile.jobs.alternative_titles
    for target in all_titles:
        t = target.lower().strip()
        if not t:
            continue
        if t in title_l:
            title_score = 30
            reasons.append(f"Desired field / title match: {target}")
            break
        target_words = set(t.split())
        title_words = set(title_l.split())
        if target_words and len(target_words & title_words) >= max(1, len(target_words) * 0.5):
            title_score = max(title_score, 18)
    if title_score == 0 and all_titles:
        issues.append("Title only weakly related to desired roles")
    score += title_score

    # Skills / keywords (0-25)
    skill_hits = []
    for skill in profile.qualifications.skills + profile.qualifications.software + profile.filters.desired_keywords:
        s = skill.lower().strip()
        if s and s in combined:
            skill_hits.append(skill)
    skill_points = min(25, len(skill_hits) * 5)
    score += skill_points
    if skill_hits:
        reasons.append(f"Skills match: {', '.join(skill_hits[:5])}")
    else:
        issues.append("Few listed skills found in the job text")

    # Experience / education hints (0-10)
    exp_hits = [e for e in profile.qualifications.work_experience if e.lower() in combined]
    edu_hits = [e for e in profile.qualifications.education if e.lower() in combined]
    if exp_hits:
        score += 6
        reasons.append(f"Relevant experience mentioned: {exp_hits[0]}")
    if edu_hits:
        score += 4
        reasons.append(f"Education match: {edu_hits[0]}")

    # Languages (0-10)
    lang_hits = []
    for lang in profile.qualifications.languages:
        token = lang.split("(")[0].strip().lower()
        if token and (token in combined or token in ["deutsch", "german", "englisch", "english"]):
            # positive if job asks for a language the user has
            if any(x in combined for x in (token, "deutsch", "german", "englisch", "english")):
                lang_hits.append(lang)
    if "deutsch" in combined or "german" in combined:
        if any("deutsch" in l.lower() or "german" in l.lower() for l in profile.qualifications.languages):
            score += 8
            reasons.append("Required German language skills available")
        else:
            issues.append("German language may be required")
            if config.settings.exclude_on_missing_mandatory:
                return MatchResult(
                    score=0,
                    rejection_reasons=["Mandatory German language missing"],
                    excluded=True,
                    exclude_reason="Mandatory German language missing",
                )
    elif lang_hits:
        score += 5
        reasons.append(f"Language fit: {', '.join(lang_hits[:2])}")

    # Driving license (0-5)
    if any(x in combined for x in ("führerschein", "fuehrerschein", "driving licence", "driving license")):
        if profile.qualifications.driving_license:
            score += 5
            reasons.append("Driving license available")
        else:
            issues.append("Driving license may be required")
            if config.settings.exclude_on_missing_mandatory:
                return MatchResult(
                    score=0,
                    rejection_reasons=["Mandatory driving license missing"],
                    excluded=True,
                    exclude_reason="Mandatory driving license missing",
                )

    # Employment type (0-5)
    emp = profile.employment
    et = (job.employment_type or "").lower()
    if "teilzeit" in et or "part" in et:
        if emp.part_time:
            score += 5
            reasons.append("Part-time allowed")
        else:
            issues.append("Part-time role")
    else:
        if emp.full_time:
            score += 5
            reasons.append("Full-time")

    # Remote / hybrid preference (0-5)
    if job.remote_type == RemoteType.REMOTE.value and emp.remote:
        score += 5
        reasons.append("Remote work")
    elif job.remote_type == RemoteType.HYBRID.value and emp.hybrid:
        score += 4
        reasons.append("Hybrid work")
    elif job.remote_type == RemoteType.ONSITE.value and emp.onsite:
        score += 3

    # Distance (0-20) — already hard-excluded above 20 km when required
    d_pts, d_reason, d_issue = _distance_points(job.distance_km, job.remote_type)
    score += d_pts
    if d_reason:
        reasons.append(d_reason)
    if d_issue:
        issues.append(d_issue)

    # Salary (0-10)
    min_sal = emp.minimum_salary
    if min_sal is None:
        score += 5
    else:
        salary_num = None
        if job.salary_min is not None:
            salary_num = int(job.salary_min)
        elif job.salary_text:
            salary_num = _extract_salary_number(job.salary_text)
        if salary_num is None:
            score += 4
            issues.append("Salary not listed")
        elif salary_num >= min_sal:
            score += 10
            reasons.append(f"Salary meets minimum ({salary_num})")
        else:
            issues.append(f"Salary below minimum ({salary_num} < {min_sal})")

    # Preferred company bonus
    for preferred in profile.filters.preferred_companies:
        if preferred.lower() in job.company.lower():
            score = min(100, score + 5)
            reasons.append(f"Preferred company: {job.company}")
            break

    score = max(0, min(100, score))
    return MatchResult(score=score, match_reasons=reasons, rejection_reasons=issues)
