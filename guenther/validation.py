"""Validate untrusted LLM output — fail closed, claim guards, manual wins."""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from guenther.contracts import (
    SCHEMA_BY_NAME,
    AssociationSuggestion,
    ClaimAnchor,
    ConfidenceLevel,
    CVExtractSuggestion,
    EmailClassSuggestion,
    EvidenceAssistSuggestion,
    EvidenceSupport,
    GuentherEnvelope,
    InterviewPrepSuggestion,
    JobAnalysisSuggestion,
    WritingSuggestion,
)

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort JSON object extraction from model text (still untrusted)."""
    raw = (text or "").strip()
    if not raw:
        return None
    m = _JSON_FENCE.search(raw)
    if m:
        raw = m.group(1).strip()
    # Find outermost object
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    chunk = raw[start : end + 1]
    try:
        data = json.loads(chunk)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def parse_contract(schema_name: str, payload: dict[str, Any] | str | None) -> BaseModel | None:
    cls = SCHEMA_BY_NAME.get(schema_name)
    if cls is None or payload is None:
        return None
    if isinstance(payload, str):
        obj = extract_json_object(payload)
        if obj is None:
            return None
        payload = obj
    try:
        return cls.model_validate(payload)
    except ValidationError:
        return None


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _token_set(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-ZäöüÄÖÜß0-9]{3,}", _norm(text))}


def claim_supported_by_corpus(claim: str, corpus: str, *, min_overlap: int = 1) -> bool:
    """True if claim tokens appear in trusted corpus (profile/job/email/evidence)."""
    c = _token_set(claim)
    if not c:
        return False
    body = _token_set(corpus)
    return len(c & body) >= min_overlap


def filter_anchors(
    anchors: list[ClaimAnchor],
    *,
    profile_text: str = "",
    job_text: str = "",
    email_text: str = "",
    evidence_text: str = "",
    manual_text: str = "",
) -> list[ClaimAnchor]:
    allowed: list[ClaimAnchor] = []
    corpora = {
        "profile": profile_text,
        "cv": profile_text,
        "job": job_text,
        "email": email_text,
        "evidence": evidence_text,
        "manual": manual_text or profile_text,
    }
    for a in anchors:
        corpus = corpora.get(a.source, "")
        quote = a.quote or a.text
        if claim_supported_by_corpus(quote, corpus) or (
            a.quote and _norm(a.quote) and _norm(a.quote) in _norm(corpus)
        ):
            allowed.append(a)
    return allowed


def demote_high_confidence(level: ConfidenceLevel, *, ok: bool) -> ConfidenceLevel:
    if not ok:
        return ConfidenceLevel.LOW
    return level


def validate_cv_extract(
    model: CVExtractSuggestion,
    *,
    cv_text: str,
    manual_profile: dict[str, Any] | None = None,
) -> tuple[CVExtractSuggestion, list[str]]:
    notes: list[str] = []
    manual = manual_profile or {}
    # Manual data wins — overwrite non-empty manual fields
    if manual.get("full_name"):
        model.full_name = str(manual["full_name"])
        notes.append("manual_name_wins")
    # Drop skills/titles not grounded in CV text
    grounded_skills = [s for s in model.skills if claim_supported_by_corpus(s, cv_text)]
    if len(grounded_skills) < len(model.skills):
        notes.append("ungrounded_skills_dropped")
        model.invented_flag = True
    model.skills = grounded_skills
    grounded_titles = [
        t for t in model.experience_titles if claim_supported_by_corpus(t, cv_text)
    ]
    if len(grounded_titles) < len(model.experience_titles):
        notes.append("ungrounded_titles_dropped")
        model.invented_flag = True
    model.experience_titles = grounded_titles
    grounded_edu = [e for e in model.education if claim_supported_by_corpus(e, cv_text)]
    if len(grounded_edu) < len(model.education):
        notes.append("ungrounded_education_dropped")
        model.invented_flag = True
    model.education = grounded_edu
    if model.invented_flag:
        model.confidence = ConfidenceLevel.LOW
    return model, notes


def validate_job_analysis(
    model: JobAnalysisSuggestion, *, job_text: str
) -> tuple[JobAnalysisSuggestion, list[str]]:
    notes: list[str] = []
    kept = []
    for item in model.requirements:
        if claim_supported_by_corpus(item.requirement, job_text):
            kept.append(item)
        else:
            notes.append("ungrounded_requirement_dropped")
    model.requirements = kept
    if notes:
        model.confidence = ConfidenceLevel.LOW
    return model, notes


def validate_evidence_assist(
    model: EvidenceAssistSuggestion,
    *,
    profile_text: str,
    job_text: str,
    existing_evidence: list[dict[str, Any]] | None = None,
) -> tuple[EvidenceAssistSuggestion, list[str]]:
    """Never upgrade NOT_SUPPORTED → DIRECT without profile tokens."""
    notes: list[str] = []
    existing = {
        _norm(str(e.get("claim") or e.get("requirement") or "")): str(
            e.get("support") or e.get("level") or ""
        ).upper()
        for e in (existing_evidence or [])
    }
    cleaned: list = []
    for item in model.items:
        key = _norm(item.claim)
        prior = existing.get(key)
        if prior == "NOT_SUPPORTED" and item.support == EvidenceSupport.DIRECT:
            item.support = EvidenceSupport.NOT_SUPPORTED
            notes.append("blocked_unsupported_to_direct")
        if item.support == EvidenceSupport.DIRECT and not claim_supported_by_corpus(
            item.claim, profile_text
        ):
            item.support = EvidenceSupport.NOT_SUPPORTED
            notes.append("direct_without_profile_demoted")
        item.anchors = filter_anchors(
            item.anchors, profile_text=profile_text, job_text=job_text, evidence_text=profile_text
        )
        cleaned.append(item)
    model.items = cleaned
    if notes:
        model.confidence = ConfidenceLevel.LOW
    return model, notes


def validate_email_class(
    model: EmailClassSuggestion,
    *,
    deterministic_category: str | None = None,
    deterministic_false_rejection_blocked: bool = False,
) -> tuple[EmailClassSuggestion, list[str]]:
    notes: list[str] = []
    if deterministic_false_rejection_blocked and model.category == "rejection":
        model.category = deterministic_category or "other"
        model.false_rejection_risk = True
        model.confidence = ConfidenceLevel.LOW
        notes.append("false_rejection_guard")
    # Never force HIGH over weak signal
    if model.confidence == ConfidenceLevel.HIGH and model.category in {"other", "noise"}:
        model.confidence = ConfidenceLevel.LOW
        notes.append("high_confidence_demoted_for_weak_category")
    return model, notes


def validate_association(
    model: AssociationSuggestion,
    *,
    known_case_ids: set[str] | None = None,
    deterministic_ambiguous: bool = False,
) -> tuple[AssociationSuggestion, list[str]]:
    """Fail closed: ambiguous or unknown case_id → no HIGH confidence silent link."""
    notes: list[str] = []
    known = known_case_ids or set()
    if model.case_id and model.case_id not in known:
        notes.append("unknown_case_id")
        model.case_id = None
        model.ambiguous = True
        model.confidence = ConfidenceLevel.LOW
    if deterministic_ambiguous:
        model.ambiguous = True
        model.confidence = ConfidenceLevel.LOW
        notes.append("deterministic_ambiguous_wins")
    if model.ambiguous or not model.case_id:
        if model.confidence == ConfidenceLevel.HIGH:
            notes.append("blocked_high_confidence_ambiguous")
        model.confidence = ConfidenceLevel.LOW
        # Keep candidates for review UI; do not silently associate
        if model.ambiguous:
            model.case_id = None
    return model, notes


def validate_writing(
    model: WritingSuggestion,
    *,
    profile_text: str,
    job_text: str,
    allowed_facts: list[str] | None = None,
) -> tuple[WritingSuggestion, list[str]]:
    notes: list[str] = []
    corpus = f"{profile_text}\n{job_text}\n" + "\n".join(allowed_facts or [])
    model.anchors_used = filter_anchors(
        model.anchors_used, profile_text=profile_text, job_text=job_text, manual_text=corpus
    )
    # Heuristic: employer/degree-like invented phrases — if body mentions
    # tokens that look like companies not in corpus, flag (lightweight).
    body_tokens = _token_set(model.body)
    corpus_tokens = _token_set(corpus)
    suspicious = {
        t
        for t in body_tokens
        if len(t) >= 6 and t not in corpus_tokens and t[0].isalpha()
    }
    # Only flag if many novel long tokens (avoid false positives on glue)
    if len(suspicious) >= 8:
        model.invented_flag = True
        model.confidence = ConfidenceLevel.LOW
        notes.append("possible_invented_facts")
    return model, notes


def validate_interview_prep(
    model: InterviewPrepSuggestion,
    *,
    profile_text: str,
    job_text: str,
    evidence_text: str,
) -> tuple[InterviewPrepSuggestion, list[str]]:
    notes: list[str] = []
    model.anchors_used = filter_anchors(
        model.anchors_used,
        profile_text=profile_text,
        job_text=job_text,
        evidence_text=evidence_text,
    )
    # Talking points must be grounded
    grounded = [
        tp
        for tp in model.talking_points
        if claim_supported_by_corpus(tp, f"{profile_text}\n{evidence_text}\n{job_text}")
    ]
    if len(grounded) < len(model.talking_points):
        notes.append("ungrounded_talking_points_dropped")
        model.invented_flag = True
        model.confidence = ConfidenceLevel.LOW
    model.talking_points = grounded
    return model, notes


def envelope_from_model(
    *,
    capability: str,
    model: BaseModel | None,
    ok: bool,
    fallback_reason: str = "",
    provider_status: str = "",
    model_id: str = "",
    safety_notes: list[str] | None = None,
    validated: bool = False,
) -> GuentherEnvelope:
    return GuentherEnvelope(
        ok=ok and model is not None,
        capability=capability,
        suggestion=model.model_dump(mode="json") if model is not None else {},
        fallback_reason=fallback_reason,
        provider_status=provider_status,
        model_id=model_id,
        validated=validated,
        safety_notes=list(safety_notes or []),
    )
