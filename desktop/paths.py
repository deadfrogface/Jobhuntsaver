"""Application data paths under %LOCALAPPDATA%\\Jobhuntsaver."""

from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "Jobhuntsaver"


def project_root() -> Path:
    """Source tree root (or frozen bundle root)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_app_dirs() -> dict[str, Path]:
    root = app_data_dir()
    dirs = {
        "root": root,
        "config": root / "config",
        "data": root / "data",
        "logs": root / "logs",
        "browser_profile": root / "browser_profile",
        "cvs": root / "cvs",
        "cache": root / "cache",
        "cover_letters": root / "cover_letters",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs
