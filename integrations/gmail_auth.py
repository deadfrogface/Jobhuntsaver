"""Gmail OAuth (readonly) — adapted from GmailJobTracker gmail_auth.py (MIT).

Uses google-auth / google-auth-oauthlib when installed. Tokens via
integrations.secure_tokens (keyring / private file). Scope is readonly only.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from integrations.secure_tokens import delete_token, load_token, store_token

logger = logging.getLogger("karrierekrake.gmail")

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
SCOPES = [GMAIL_READONLY_SCOPE]
TOKEN_ACCOUNT = "gmail_readonly"


def gmail_libs_available() -> bool:
    try:
        import google.auth.transport.requests  # noqa: F401
        from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: F401
        from googleapiclient.discovery import build  # noqa: F401

        return True
    except Exception:
        return False


def _oauth_port(default: int = 8080) -> int:
    import os

    raw = os.environ.get("GMAIL_OAUTH_PORT", str(default)).strip()
    try:
        port = int(raw)
        return port if port > 0 else default
    except ValueError:
        return default


def load_client_config(credentials_path: Path) -> tuple[str, dict] | tuple[None, None]:
    try:
        config = json.loads(Path(credentials_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("OAuth client config unreadable: %s", type(exc).__name__)
        return None, None
    if "installed" in config:
        return "installed", config["installed"]
    if "web" in config:
        return "web", config["web"]
    return None, None


def resolve_oauth_port(client_type: str, client_config: dict) -> int | None:
    requested = _oauth_port()
    if client_type == "installed":
        return requested
    redirect_uris = client_config.get("redirect_uris", []) or []
    localhost = []
    for uri in redirect_uris:
        parsed = urlparse(uri)
        if parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}:
            localhost.append(parsed)
    for parsed in localhost:
        if (parsed.port or 80) == requested:
            return requested
    logger.error("Web OAuth client needs localhost redirect for port %s", requested)
    return None


def save_creds_payload(creds: Any, *, fallback_dir: Path) -> str:
    payload = {
        "token": getattr(creds, "token", None),
        "refresh_token": getattr(creds, "refresh_token", None),
        "token_uri": getattr(creds, "token_uri", None),
        "client_id": getattr(creds, "client_id", None),
        "client_secret": getattr(creds, "client_secret", None),
        "scopes": list(getattr(creds, "scopes", None) or SCOPES),
        "expiry": creds.expiry.isoformat() if getattr(creds, "expiry", None) else None,
    }
    return store_token(TOKEN_ACCOUNT, payload, fallback_dir=fallback_dir)


def creds_from_payload(payload: dict[str, Any]):
    from google.oauth2.credentials import Credentials

    return Credentials(
        token=payload.get("token"),
        refresh_token=payload.get("refresh_token"),
        token_uri=payload.get("token_uri") or "https://oauth2.googleapis.com/token",
        client_id=payload.get("client_id"),
        client_secret=payload.get("client_secret"),
        scopes=payload.get("scopes") or SCOPES,
    )


def get_gmail_service(*, credentials_path: Path, token_dir: Path):
    """Authorize and return Gmail API resource (readonly) or None."""
    if not gmail_libs_available():
        logger.warning("Google API libraries not installed — Gmail disabled")
        return None

    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    payload = load_token(TOKEN_ACCOUNT, fallback_dir=token_dir)
    if payload:
        try:
            creds = creds_from_payload(payload)
        except Exception as exc:
            logger.warning("Stored Gmail token unusable: %s", type(exc).__name__)
            creds = None

    try:
        if creds and not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                save_creds_payload(creds, fallback_dir=token_dir)
            else:
                creds = None
        if not creds:
            client_type, client_config = load_client_config(credentials_path)
            if not client_type or not client_config:
                return None
            port = resolve_oauth_port(client_type, client_config)
            if port is None:
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=port)
            save_creds_payload(creds, fallback_dir=token_dir)
        return build("gmail", "v1", credentials=creds, cache_discovery=False)
    except Exception as exc:
        logger.error("Gmail auth failed: %s", type(exc).__name__)
        return None


def disconnect_gmail(*, token_dir: Path) -> None:
    delete_token(TOKEN_ACCOUNT, fallback_dir=token_dir)


def gmail_connected(*, token_dir: Path) -> bool:
    payload = load_token(TOKEN_ACCOUNT, fallback_dir=token_dir)
    return bool(payload and (payload.get("refresh_token") or payload.get("token")))
