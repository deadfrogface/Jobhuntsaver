"""One-time AppData migration from the retired technical folder name.

CRITICAL: This is the ONLY module that may mention the legacy filesystem
folder name ``Jobhuntsaver``. Everywhere else must use Karrierekrake /
``karrierekrake``.

Priority: no data loss > correct migration > zero ongoing legacy identity.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from pathlib import Path

# Isolated legacy recognition — do not import this constant into UI/branding.
_LEGACY_DATA_DIR_NAME = "Jobhuntsaver"

_MARKER_NAME = ".karrierekrake_migration.json"
_logger = logging.getLogger("karrierekrake.migration")


def legacy_data_dir_name() -> str:
    """Return the retired AppData folder name (migration boundary only)."""
    return _LEGACY_DATA_DIR_NAME


def _local_appdata_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base)


def legacy_app_data_dir() -> Path:
    return _local_appdata_root() / _LEGACY_DATA_DIR_NAME


def _dir_looks_populated(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        next(path.iterdir())
        return True
    except StopIteration:
        return False
    except OSError:
        return False


def _write_marker(dest: Path, *, source: Path, status: str) -> None:
    payload = {
        "status": status,
        "product": "Karrierekrake",
        "source": str(source),
        "destination": str(dest),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    marker = dest / _MARKER_NAME
    marker.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _copy_tree_safe(src: Path, dst: Path) -> None:
    """Copy src → dst without deleting src. Skip if dst file already exists."""
    dst.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)
        target_root = dst / rel
        target_root.mkdir(parents=True, exist_ok=True)
        # Do not descend into destination if nested oddly
        dirs[:] = [d for d in dirs if d not in {".git"}]
        for name in files:
            if name == _MARKER_NAME:
                continue
            s = Path(root) / name
            t = target_root / name
            if t.exists():
                continue
            try:
                shutil.copy2(s, t)
            except OSError as exc:
                _logger.warning("migration copy failed %s → %s: %s", s, t, exc)
                raise


def migrate_legacy_appdata_if_needed(canonical_dir: Path) -> Path:
    """Ensure ``canonical_dir`` is the active AppData root.

    Behavior:
    - Fresh install: create canonical dir, return it.
    - Legacy only: copy into canonical, write marker, leave legacy intact.
    - Canonical already present: use it (idempotent); optionally top-up
      missing files from legacy once if marker missing and legacy exists.
    - Never delete the legacy folder automatically.
    """
    legacy = legacy_app_data_dir()
    marker = canonical_dir / _MARKER_NAME
    legacy_populated = False

    try:
        if marker.is_file():
            canonical_dir.mkdir(parents=True, exist_ok=True)
            return canonical_dir

        canonical_populated = _dir_looks_populated(canonical_dir)
        legacy_populated = _dir_looks_populated(legacy)

        if canonical_populated and not legacy_populated:
            canonical_dir.mkdir(parents=True, exist_ok=True)
            _write_marker(canonical_dir, source=canonical_dir, status="canonical_only")
            return canonical_dir

        if legacy_populated and not canonical_populated:
            canonical_dir.mkdir(parents=True, exist_ok=True)
            _copy_tree_safe(legacy, canonical_dir)
            _write_marker(canonical_dir, source=legacy, status="migrated_from_legacy")
            return canonical_dir

        if legacy_populated and canonical_populated:
            # Prefer canonical; fill gaps from legacy without overwriting.
            _copy_tree_safe(legacy, canonical_dir)
            _write_marker(canonical_dir, source=legacy, status="merged_prefer_canonical")
            return canonical_dir

        canonical_dir.mkdir(parents=True, exist_ok=True)
        return canonical_dir
    except OSError as exc:
        _logger.error("AppData migration failed: %s", exc)
        # Fail soft: if canonical usable, keep going; else fall back to legacy
        # only as last resort so users do not lose access mid-migration.
        if canonical_dir.is_dir() or not legacy_populated:
            canonical_dir.mkdir(parents=True, exist_ok=True)
            return canonical_dir
        _logger.error("Using legacy AppData path temporarily after migration failure")
        return legacy
