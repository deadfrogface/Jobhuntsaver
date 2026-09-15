"""Secure local token storage for Gmail/Calendar OAuth.

Prefer OS credential stores (Windows Credential Locker via keyring when
available). Fall back to a mode-0600 JSON file under the app private dir.
Never log token values.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("karrierekrake.tokens")

SERVICE_NAME = "Karrierekrake"


def _keyring():
    try:
        import keyring  # type: ignore

        return keyring
    except Exception:
        return None


def store_token(account: str, payload: dict[str, Any], *, fallback_dir: Path) -> str:
    """Persist token dict. Returns backend used: 'keyring' | 'file'."""
    raw = json.dumps(payload, ensure_ascii=False)
    kr = _keyring()
    if kr is not None:
        try:
            kr.set_password(SERVICE_NAME, account, raw)
            return "keyring"
        except Exception as exc:
            logger.warning("keyring store failed, using file fallback: %s", type(exc).__name__)
    path = Path(fallback_dir) / f"oauth_{account}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return "file"


def load_token(account: str, *, fallback_dir: Path) -> dict[str, Any] | None:
    kr = _keyring()
    if kr is not None:
        try:
            raw = kr.get_password(SERVICE_NAME, account)
            if raw:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
        except Exception as exc:
            logger.warning("keyring load failed: %s", type(exc).__name__)
    path = Path(fallback_dir) / f"oauth_{account}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def delete_token(account: str, *, fallback_dir: Path) -> None:
    kr = _keyring()
    if kr is not None:
        try:
            kr.delete_password(SERVICE_NAME, account)
        except Exception:
            pass
    path = Path(fallback_dir) / f"oauth_{account}.json"
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass
