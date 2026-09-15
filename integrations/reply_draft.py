"""Employer reply drafting — draft-only by default; approval before send.

Templates adapted from PBP nachfass_text ideas (MIT). No cloud AI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.models import utc_now_iso


@dataclass
class ReplyDraft:
    case_id: str
    to_address: str
    subject: str
    body: str
    created_at: str = field(default_factory=utc_now_iso)
    approved: bool = False
    sent: bool = False
    send_error: str = ""
    draft_only: bool = True


def build_follow_up_draft(case: dict[str, Any], *, applicant_name: str = "") -> ReplyDraft:
    company = case.get("company") or "Ihr Unternehmen"
    position = case.get("position") or case.get("title") or "die ausgeschriebene Position"
    contact = (case.get("contact_name") or "").strip()
    to_addr = (case.get("contact_email") or "").strip()
    greeting = f"Guten Tag {contact}," if contact else "Guten Tag,"
    name = (applicant_name or "").strip() or "…"
    body = (
        f"{greeting}\n\n"
        f"kurz möchte ich höflich nach dem Stand meiner Bewerbung als {position} "
        f"bei {company} fragen. Ich bleibe weiterhin sehr interessiert und stehe "
        f"für Rückfragen gerne zur Verfügung.\n\n"
        f"Mit freundlichen Grüßen\n{name}\n"
    )
    subject = f"Nachfrage zur Bewerbung — {position}"
    return ReplyDraft(
        case_id=str(case.get("id") or ""),
        to_address=to_addr,
        subject=subject,
        body=body,
        draft_only=True,
        approved=False,
        sent=False,
    )


def build_interview_confirm_draft(
    case: dict[str, Any],
    *,
    when_text: str = "",
    applicant_name: str = "",
    offer_phone: bool = False,
    phone: str = "",
) -> ReplyDraft:
    contact = (case.get("contact_name") or "").strip()
    greeting = f"Guten Tag {contact}," if contact else "Guten Tag,"
    name = (applicant_name or "").strip() or "…"
    when_line = f" am {when_text}" if when_text else ""
    phone_line = ""
    if offer_phone and phone:
        phone_line = f"\nUnter {phone} bin ich in den genannten Zeitfenstern telefonisch erreichbar.\n"
    body = (
        f"{greeting}\n\n"
        f"vielen Dank für die Einladung. Den vorgeschlagenen Termin{when_line} "
        f"kann ich wahrnehmen.{phone_line}\n"
        f"Mit freundlichen Grüßen\n{name}\n"
    )
    return ReplyDraft(
        case_id=str(case.get("id") or ""),
        to_address=(case.get("contact_email") or "").strip(),
        subject="Bestätigung Interviewtermin",
        body=body,
        draft_only=True,
    )


class SendGate:
    """Approval-before-send + failure safety. Default refuses real send."""

    def __init__(self, *, allow_send: bool = False) -> None:
        self.allow_send = bool(allow_send)

    def approve(self, draft: ReplyDraft) -> ReplyDraft:
        draft.approved = True
        return draft

    def attempt_send(self, draft: ReplyDraft, *, transport) -> ReplyDraft:
        """Call transport(draft) only when approved and allow_send.

        On failure: mark send_error, leave sent=False, keep draft for retry.
        Never silently drop the draft.
        """
        if draft.draft_only and not self.allow_send:
            draft.send_error = "draft_only: send disabled (approval path required)"
            draft.sent = False
            return draft
        if not draft.approved:
            draft.send_error = "not_approved"
            draft.sent = False
            return draft
        if not self.allow_send:
            draft.send_error = "send_not_enabled"
            draft.sent = False
            return draft
        try:
            transport(draft)
            draft.sent = True
            draft.send_error = ""
        except Exception as exc:
            draft.sent = False
            draft.send_error = f"send_failed: {type(exc).__name__}: {exc}"
        return draft
