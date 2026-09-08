"""Local job matching (0-100) without LLM APIs.

Uses the full structured profile: titles, experience, education,
certificates, software, skills, languages+levels, driving license.
"""

from __future__ import annotations

import re

from core.config import AppConfig, LanguageEntry
from core.hard_filter import hard_exclude
from core.models import Job, MatchResult, RemoteType

_CEFR_ORDER = {"a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6, "muttersprache": 6, "native": 6}


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


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _token_in_text(token: str, haystack: str) -> bool:
    t = _norm(token)
    if not t or len(t) < 2:
        return False
    if t in haystack:
        return True
    # Word-boundary-ish for short tokens
    return bool(re.search(rf"(?<!\w){re.escape(t)}(?!\w)", haystack))


def _required_language_levels(text: str) -> list[tuple[str, str]]:
    """Detect language requirements like 'Englisch C1' in a job ad."""
    found: list[tuple[str, str]] = []
    patterns = [
        r"(deutsch|german|englisch|english|französisch|franzoesisch|french|italienisch|italian|spanisch|spanish|ungarisch|hungarian)\s*(?:kenntnisse)?\s*[\(:]?\s*([abc][12]|muttersprache|native)",
        r"([abc][12])\s+(deutsch|german|englisch|english)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            g1, g2 = m.group(1), m.group(2)
            if re.fullmatch(r"[abc][12]", g1, re.I):
                found.append((_norm(g2), g1.upper()))
            else:
                found.append((_norm(g1), g2.upper() if len(g2) == 2 else g2))
    return found


def _profile_lang_level(languages: list[LanguageEntry], name: str) -> int:
    aliases = {
        "deutsch": {"deutsch", "german"},
        "german": {"deutsch", "german"},
        "englisch": {"englisch", "english"},
        "english": {"englisch", "english"},
        "italienisch": {"italienisch", "italian"},
        "ungarisch": {"ungarisch", "hungarian"},
    }
    wanted = aliases.get(name, {name})
    best = 0
    for lang in languages:
        if _norm(lang.language) in wanted or any(a in _norm(lang.language) for a in wanted):
            best = max(best, _CEFR_ORDER.get(_norm(lang.level), 0))
    return best


def _has_driving_class_b(licenses: list[str], text: str) -> bool:
    joined = " ".join(licenses).lower()
    return bool(re.search(r"klasse\s*b|\b[b]\b.*pkw|führerschein\s*b", joined))


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
    quals = profile.qualifications
    reasons: list[str] = []
    issues: list[str] = []
    score = 0

    title_l = _norm(job.title)
    desc_l = _norm(job.description or "")
    combined = f"{title_l} {desc_l}"

    # Title match (0-30)
    title_score = 0
    all_titles = profile.jobs.desired_titles + profile.jobs.alternative_titles
    # Also consider past job titles from experience
    past_titles = [e.title for e in quals.work_experience if e.title]
    for target in all_titles:
        t = _norm(target)
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
    if title_score < 30:
        for past in past_titles:
            if _norm(past) and _norm(past) in title_l:
                title_score = max(title_score, 22)
                reasons.append(f"Title matches prior role: {past}")
                break
            past_words = set(_norm(past).split())
            if past_words and len(past_words & set(title_l.split())) >= max(1, len(past_words) * 0.5):
                title_score = max(title_score, 16)
    if title_score == 0 and (all_titles or past_titles):
        issues.append("Title only weakly related to desired roles")
    score += title_score

    # Skills / software / certificates / keywords (0-25)
    skill_hits: list[str] = []
    candidates = (
        list(quals.skills)
        + list(quals.software)
        + list(profile.filters.desired_keywords)
        + [c.name for c in quals.certificates if c.name]
    )
    for skill in candidates:
        if _token_in_text(skill, combined) or any(
            _token_in_text(part, combined)
            for part in re.split(r"[,/|]", skill)
            if len(part.strip()) >= 3
        ):
            skill_hits.append(skill)
    skill_points = min(25, len(dict.fromkeys(skill_hits)) * 5)
    score += skill_points
    if skill_hits:
        reasons.append(f"Skills/software match: {', '.join(list(dict.fromkeys(skill_hits))[:5])}")
    else:
        issues.append("Few listed skills found in the job text")

    # Experience responsibilities / education (0-15)
    exp_hits: list[str] = []
    for exp in quals.work_experience:
        for token in exp.search_tokens():
            # Prefer meaningful phrases (>= 4 chars)
            if len(token.strip()) < 4:
                continue
            if _token_in_text(token, combined):
                exp_hits.append(token)
                break
            # Partial: key nouns from responsibilities
            for word in re.findall(r"[A-Za-zÄÖÜäöüß]{5,}", token):
                if _token_in_text(word, combined):
                    exp_hits.append(word)
                    break
    edu_hits: list[str] = []
    for edu in quals.education:
        for token in edu.search_tokens():
            if len(token.strip()) >= 4 and _token_in_text(token, combined):
                edu_hits.append(token)
    if exp_hits:
        score += min(10, 4 + len(exp_hits))
        reasons.append(f"Relevant experience: {', '.join(list(dict.fromkeys(exp_hits))[:3])}")
    if edu_hits:
        score += 4
        reasons.append(f"Education match: {edu_hits[0]}")

    # Languages + proficiency (0-10)
    lang_req = _required_language_levels(combined)
    if lang_req:
        satisfied = []
        missing = []
        for name, level in lang_req:
            have = _profile_lang_level(quals.languages, name)
            need = _CEFR_ORDER.get(level.lower(), 0)
            if have and have >= need:
                satisfied.append(f"{name} {level}")
            elif have:
                missing.append(f"{name} {level} (profile lower)")
            else:
                missing.append(f"{name} {level}")
        if satisfied:
            score += min(10, 5 + 2 * len(satisfied))
            reasons.append(f"Language requirement met: {', '.join(satisfied[:3])}")
        if missing:
            issues.append(f"Language may be missing: {', '.join(missing[:2])}")
            if config.settings.exclude_on_missing_mandatory and any(
                "deutsch" in m or "german" in m for m in missing
            ):
                return MatchResult(
                    score=0,
                    rejection_reasons=["Mandatory German language missing"],
                    excluded=True,
                    exclude_reason="Mandatory German language missing",
                )
    else:
        # Soft language presence
        if any("deutsch" in _norm(l.language) or "german" in _norm(l.language) for l in quals.languages):
            if "deutsch" in combined or "german" in combined:
                score += 6
                reasons.append("German language skills available")

    # Driving license (0-5)
    needs_license = any(
        x in combined
        for x in ("führerschein", "fuehrerschein", "driving licence", "driving license", "klasse b")
    )
    if needs_license:
        if quals.driving_license:
            if "klasse b" in combined or re.search(r"führerschein\s*b|\bklasse\s*b\b", combined):
                if _has_driving_class_b(quals.driving_license, combined):
                    score += 5
                    reasons.append("Driving license Klasse B available")
                elif quals.driving_license:
                    score += 3
                    reasons.append("Driving license available")
            else:
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

    d_pts, d_reason, d_issue = _distance_points(job.distance_km, job.remote_type)
    score += d_pts
    if d_reason:
        reasons.append(d_reason)
    if d_issue:
        issues.append(d_issue)

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

    for preferred in profile.filters.preferred_companies:
        if preferred.lower() in job.company.lower():
            score = min(100, score + 5)
            reasons.append(f"Preferred company: {job.company}")
            break

    score = max(0, min(100, score))
    return MatchResult(score=score, match_reasons=reasons, rejection_reasons=issues)
