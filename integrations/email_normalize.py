"""Email body normalization for classification / association.

Adapted from PBP email_service (MIT) and GmailJobTracker EmailBodyParser (MIT).
No Django dependency.
"""

from __future__ import annotations

import base64
import re
from email.utils import parseaddr
from html import unescape
from typing import Any


_TAG_RE = re.compile(r"<[^>]+>")
_STYLE_RE = re.compile(r"<style[^>]*>[\s\S]*?</style>", re.I)
_SCRIPT_RE = re.compile(r"<script[^>]*>[\s\S]*?</script>", re.I)
_QUOTE_RE = re.compile(
    r"(?:^|\n)(?:>.*(?:\n|$)|On .+ wrote:.*|Am .+ schrieb .+:.*|"
    r"-{2,}\s*Original Message\s*-{2,}.*|"
    r"Von:.*\nGesendet:.*)",
    re.I | re.S,
)


def html_to_plaintext(html: str) -> str:
    text = _STYLE_RE.sub(" ", html or "")
    text = _SCRIPT_RE.sub(" ", text)
    text = _TAG_RE.sub(" ", text)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def strip_quoted_reply(text: str) -> str:
    if not text:
        return ""
    m = _QUOTE_RE.search(text)
    if m and m.start() > 40:
        return text[: m.start()].strip()
    return text.strip()


def extract_sender_email(sender: str) -> str:
    _, addr = parseaddr(sender or "")
    return (addr or "").strip().lower()


def extract_sender_domain(sender: str) -> str:
    email = extract_sender_email(sender)
    if "@" in email:
        return email.split("@", 1)[1].lower()
    return ""


def decode_gmail_body_data(data: str) -> str:
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extract_from_gmail_parts(parts: list[dict[str, Any]]) -> str:
    """Prefer HTML, fall back to plain text (GmailJobTracker EmailBodyParser)."""
    plain_fallback = ""
    for part in parts or []:
        mime = (part.get("mimeType") or "").lower()
        body_data = (part.get("body") or {}).get("data")
        if mime == "text/html" and body_data:
            decoded = decode_gmail_body_data(body_data)
            if decoded:
                return decoded
        elif mime == "text/plain" and body_data and not plain_fallback:
            plain_fallback = decode_gmail_body_data(body_data)
        nested = part.get("parts") or []
        if nested:
            result = extract_from_gmail_parts(nested)
            if result:
                return result
    return plain_fallback


def normalize_email_text(subject: str, body_html_or_text: str) -> str:
    body = body_html_or_text or ""
    if "<" in body and ">" in body:
        body = html_to_plaintext(body)
    body = strip_quoted_reply(body)
    # Drop URLs so they do not dominate phrase matching (ejobtrack ponytail idea).
    body = re.sub(r"https?://\S+", " ", body)
    combined = f"{subject or ''}\n{body}"
    return re.sub(r"\s+", " ", combined).strip()


def normalize_umlauts(text: str) -> str:
    return (
        (text or "")
        .lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
