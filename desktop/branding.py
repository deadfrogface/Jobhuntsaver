"""Central product branding — display name is changeable; data paths stay stable.

Internal / filesystem identity remains ``Jobhuntsaver`` so existing
``%LOCALAPPDATA%\\Jobhuntsaver`` trees, Task Scheduler names, smoke markers,
and EXE filenames keep working without a risky migration.
"""

from __future__ import annotations

from pathlib import Path

# --- Stable technical identity (do not change lightly) ---
TECHNICAL_NAME = "Jobhuntsaver"
DATA_DIR_NAME = "Jobhuntsaver"
EXE_BASENAME = "Jobhuntsaver"
SINGLE_INSTANCE_KEY = "JobhuntsaverSingleInstance"
LOCAL_SERVER_NAME = "JobhuntsaverLocalServer"
TASK_SCHEDULER_NAME = "JobhuntsaverAutoRun"
ORG_DOMAIN = "jobhuntsaver.local"
USER_AGENT = "Jobhuntsaver/1.0 (local personal use)"

# --- User-facing product brand (changeable) ---
DISPLAY_NAME = "Stellenanker"
TAGLINE_DE = "Lokale Jobsuche & Bewerbungen für Deutschland"
TAGLINE_EN = "Local job search & applications for Germany"
SHORT_DESCRIPTION_DE = (
    "Desktop-App für die Jobsuche in Deutschland: finden, bewerten, "
    "Bewerbungen vorbereiten — alles lokal auf Ihrem PC."
)
SHORT_DESCRIPTION_EN = (
    "Desktop app for job search in Germany: find, score, and prepare "
    "applications — everything stays on your PC."
)

# Brand colors (restrained teal / slate — not purple-on-white)
COLOR_PRIMARY = "#1F6B5C"
COLOR_PRIMARY_HOVER = "#18574B"
COLOR_ACCENT = "#C45C26"
COLOR_SIDEBAR_TOP = "#143D48"
COLOR_SIDEBAR_BOTTOM = "#0B282F"
COLOR_LIGHT_BG = "#F0F4F7"
COLOR_DARK_BG = "#121820"
COLOR_MARK = "#F4F7FA"

# Asset layout relative to repo / frozen bundle
ASSET_REL = Path("assets") / "brand"


def _asset_roots() -> list[Path]:
    """Candidate roots that may contain ``assets/brand`` (dev + frozen)."""
    import sys

    from desktop.paths import project_root

    roots: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))
    roots.append(project_root())
    # Deduplicate
    seen: set[str] = set()
    out: list[Path] = []
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        out.append(root)
    return out


def project_assets_dir() -> Path:
    """Return the first existing ``assets/brand`` directory."""
    for root in _asset_roots():
        candidate = root / ASSET_REL
        if candidate.is_dir():
            return candidate
    return _asset_roots()[0] / ASSET_REL


def icon_path(size: int | None = None) -> Path | None:
    """Prefer ICO for Windows, then sized PNG, then logo PNG."""
    for root in _asset_roots():
        base = root / ASSET_REL
        candidates: list[Path] = []
        if size:
            candidates.append(base / "icons" / f"icon-{size}.png")
        candidates.extend(
            [
                base / "app.ico",
                base / "icons" / "icon-256.png",
                base / "icons" / "icon-128.png",
                base / "logo.png",
            ]
        )
        for path in candidates:
            if path.is_file():
                return path
    return None


def social_preview_path() -> Path | None:
    path = project_assets_dir() / "social-preview.png"
    return path if path.is_file() else None


def display_name() -> str:
    return DISPLAY_NAME


def tagline(language: str = "de") -> str:
    return TAGLINE_EN if (language or "de").lower().startswith("en") else TAGLINE_DE
