"""Follow-up / ghosted suggestions — suggest only, never auto-send.

Adapted from PBP nachfass_text (MIT, Claude prompt rejected) and
trackjobapplications needsFollowUp (MIT).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from core.lifecycle import CaseStatus, TERMINAL_STATUSES


# PBP UEBERHOLTE_STATUS idea — routine follow-up obsolete.
SUPERSEDED_STATUSES = frozenset(
    {
        CaseStatus.INTERVIEW.value,
        CaseStatus.OFFER.value,
        CaseStatus.REJECTED.value,
        CaseStatus.WITHDRAWN.value,
        CaseStatus.CLOSED.value,
        CaseStatus.ASSESSMENT.value,
    }
)


@dataclass(frozen=True)
class FollowUpSuggestion:
    case_id: str
    urgency: int
    text: str
    kind: str  # follow_up | ghosted
    auto_send: bool = False  # always False by product rule


def _parse_dt(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def days_since(iso: str, *, now: datetime | None = None) -> float | None:
    dt = _parse_dt(iso)
    if not dt:
        return None
    now = now or datetime.now(timezone.utc)
    return (now - dt.astimezone(timezone.utc)).total_seconds() / 86400.0


def follow_up_text(case: dict[str, Any], *, anlass: str = "") -> str:
    """Actionable follow-up description (PBP nachfass_text, no Claude)."""
    title = case.get("position") or case.get("title") or "?"
    company = case.get("company") or "?"
    head = f"Nachfassen zur Bewerbung als {title} bei {company}"
    applied = (case.get("applied_at") or "")[:10]
    if applied:
        head += f" (beworben am {applied})"
    parts = [head]
    contact = (case.get("contact_name") or "").strip()
    mail = (case.get("contact_email") or "").strip()
    if contact and mail:
        parts.append(f"Ansprechpartner: {contact} ({mail})")
    elif contact:
        parts.append(f"Ansprechpartner: {contact}")
    elif mail:
        parts.append(f"Kontakt: {mail}")
    status = (case.get("status") or "").strip()
    if status:
        parts.append(f"Stand: {status}")
    if anlass:
        parts.append(anlass)
    elif status == CaseStatus.INTERVIEW.value:
        parts.append("Nach dem Ergebnis des Gesprächs fragen und Interesse bekräftigen.")
    else:
        parts.append("Kurz freundlich nach dem Stand fragen und auf die Bewerbung Bezug nehmen.")
    return " — ".join(parts)


def is_follow_up_obsolete(case: dict[str, Any], meetings: list[dict[str, Any]] | None = None) -> tuple[bool, str]:
    status = (case.get("status") or "").lower()
    if status in SUPERSEDED_STATUSES and status != CaseStatus.INTERVIEW.value:
        # Interview still may need post-interview follow-up; other superseded clear.
        if status in TERMINAL_STATUSES | {CaseStatus.OFFER.value, CaseStatus.ASSESSMENT.value}:
            return True, f"Stand ist '{status}' — Routine-Nachfrage erübrigt sich."
    if status in TERMINAL_STATUSES:
        return True, f"Stand ist '{status}' — Routine-Nachfrage erübrigt sich."
    for m in meetings or []:
        when = str(m.get("scheduled_at") or m.get("datum") or "")[:10]
        if when:
            return True, f"Termin am {when} vereinbart — Nachfrage erledigt."
    return False, ""


def suggest_follow_ups(
    cases: list[dict[str, Any]],
    *,
    follow_up_days: int = 14,
    ghosted_days: int = 21,
    now: datetime | None = None,
) -> list[FollowUpSuggestion]:
    """Suggest follow-up / ghosted tasks. Never sets auto_send."""
    now = now or datetime.now(timezone.utc)
    out: list[FollowUpSuggestion] = []
    for case in cases:
        status = (case.get("status") or "").lower()
        if status not in {
            CaseStatus.APPLIED.value,
            CaseStatus.CONFIRMATION.value,
            CaseStatus.GHOSTED.value,
            CaseStatus.INTERVIEW.value,
        }:
            continue
        obsolete, _ = is_follow_up_obsolete(case)
        if obsolete and status != CaseStatus.INTERVIEW.value:
            continue
        # Prefer applied_at for silence timers — updated_at refreshes on any
        # case touch and would hide genuine ghosting/follow-up signals.
        if status in {
            CaseStatus.APPLIED.value,
            CaseStatus.CONFIRMATION.value,
            CaseStatus.GHOSTED.value,
        }:
            anchor = case.get("applied_at") or case.get("updated_at") or case.get("created_at") or ""
        else:
            anchor = case.get("updated_at") or case.get("applied_at") or case.get("created_at") or ""
        age = days_since(anchor, now=now)
        if age is None:
            continue
        case_id = str(case.get("id") or "")
        if not case_id:
            continue
        if age >= ghosted_days and status in {
            CaseStatus.APPLIED.value,
            CaseStatus.CONFIRMATION.value,
            CaseStatus.GHOSTED.value,
        }:
            out.append(
                FollowUpSuggestion(
                    case_id=case_id,
                    urgency=2,
                    text=follow_up_text(case, anlass="Möglicherweise ohne Rückmeldung (Ghosting-Hinweis — nur Vorschlag)."),
                    kind="ghosted",
                    auto_send=False,
                )
            )
        elif age >= follow_up_days:
            out.append(
                FollowUpSuggestion(
                    case_id=case_id,
                    urgency=1,
                    text=follow_up_text(case),
                    kind="follow_up",
                    auto_send=False,
                )
            )
    out.sort(key=lambda s: (-s.urgency, s.case_id))
    return out
