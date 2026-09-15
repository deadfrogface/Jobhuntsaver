"""Gmail sync helpers — list/get/parse adapted from ejobtrack gmail.ts (Apache-2.0)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from integrations.email_normalize import (
    extract_from_gmail_parts,
    extract_sender_email,
    html_to_plaintext,
    normalize_email_text,
)

logger = logging.getLogger("karrierekrake.gmail")


@dataclass
class ParsedEmail:
    id: str
    thread_id: str = ""
    subject: str = ""
    sender: str = ""
    snippet: str = ""
    body_text: str = ""
    internal_date: str = ""
    label_ids: list[str] = field(default_factory=list)


def _header(headers: list[dict[str, str]], name: str) -> str:
    target = name.lower()
    for h in headers or []:
        if (h.get("name") or "").lower() == target:
            return h.get("value") or ""
    return ""


def parse_message(msg: dict[str, Any]) -> ParsedEmail:
    payload = msg.get("payload") or {}
    headers = payload.get("headers") or []
    subject = _header(headers, "Subject")
    sender = _header(headers, "From")
    body_html_or_text = ""
    if payload.get("parts"):
        body_html_or_text = extract_from_gmail_parts(payload["parts"])
    else:
        data = (payload.get("body") or {}).get("data")
        if data:
            from integrations.email_normalize import decode_gmail_body_data

            body_html_or_text = decode_gmail_body_data(data)
    body_text = normalize_email_text(subject, body_html_or_text)
    if not body_text and msg.get("snippet"):
        body_text = str(msg.get("snippet") or "")
    return ParsedEmail(
        id=str(msg.get("id") or ""),
        thread_id=str(msg.get("threadId") or ""),
        subject=subject,
        sender=sender,
        snippet=str(msg.get("snippet") or ""),
        body_text=body_text,
        internal_date=str(msg.get("internalDate") or ""),
        label_ids=list(msg.get("labelIds") or []),
    )


def list_message_ids(
    service,
    *,
    query: str = "newer_than:90d",
    max_results: int = 50,
    page_token: str | None = None,
) -> tuple[list[str], str | None]:
    kwargs: dict[str, Any] = {
        "userId": "me",
        "q": query,
        "maxResults": max_results,
    }
    if page_token:
        kwargs["pageToken"] = page_token
    resp = service.users().messages().list(**kwargs).execute()
    ids = [m["id"] for m in (resp.get("messages") or []) if m.get("id")]
    return ids, resp.get("nextPageToken")


def get_message(service, message_id: str) -> dict[str, Any]:
    return (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )


def sync_recent(
    service,
    *,
    query: str = "newer_than:90d (bewerbung OR application OR interview OR absage OR offer)",
    max_results: int = 40,
    on_error: Callable[[Exception], None] | None = None,
) -> list[ParsedEmail]:
    """Fetch and parse recent messages. No classification here."""
    out: list[ParsedEmail] = []
    try:
        ids, _ = list_message_ids(service, query=query, max_results=max_results)
    except Exception as exc:
        if on_error:
            on_error(exc)
        else:
            logger.warning("Gmail list failed: %s", type(exc).__name__)
        return out
    for mid in ids:
        try:
            raw = get_message(service, mid)
            out.append(parse_message(raw))
        except Exception as exc:
            if on_error:
                on_error(exc)
            else:
                logger.warning("Gmail get failed for %s: %s", mid, type(exc).__name__)
    return out


def sender_is_excluded(sender: str, excluded: list[str]) -> bool:
    """CareerSync shouldExcludeEmail adapted (MIT)."""
    from integrations.email_normalize import extract_sender_email

    if not excluded:
        return False
    email = extract_sender_email(sender).lower()
    for rule in excluded:
        r = (rule or "").lower().strip()
        if not r:
            continue
        if email == r:
            return True
        if r.startswith("*@"):
            if email.endswith("@" + r[2:]):
                return True
        elif r.startswith("@") and email.endswith(r):
            return True
        elif r in email:
            return True
    return False
