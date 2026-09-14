"""Cover letter template rendering (no paid AI required)."""

from __future__ import annotations

from collections import defaultdict

import sys
from pathlib import Path

from core.config import AppConfig
from core.models import Job


DEFAULT_TEMPLATE = """Sehr geehrte Damen und Herren,

hiermit bewerbe ich mich um die Position als {job_title} bei {company}.

{experience_sentence}

Zu meinen relevanten Kenntnissen zählen insbesondere: {skills}.

Über die Möglichkeit eines persönlichen Gesprächs freue ich mich.

Mit freundlichen Grüßen
{full_name}
"""


def _meipass_dir() -> Path | None:
    """PyInstaller extract dir when running as a frozen onefile/onedir bundle."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return None


def resolve_cover_letter_template(config: AppConfig) -> Path | None:
    """Locate the cover-letter template on disk, including frozen _MEIPASS."""
    template_path = Path(config.settings.cover_letter_template)
    candidates: list[Path] = []
    if template_path.is_absolute():
        candidates.append(template_path)
    else:
        mi = _meipass_dir()
        if mi is not None:
            # Bundled datas land under _MEIPASS, not next to the EXE.
            candidates.append(mi / template_path)
        candidates.append(config.root / template_path)
        # Dev / source-tree fallback next to package root.
        candidates.append(Path(__file__).resolve().parent.parent / template_path)
    for path in candidates:
        if path.is_file():
            return path
    return None


def render_cover_letter(job: Job, config: AppConfig) -> str:
    template_path = resolve_cover_letter_template(config)
    if template_path is not None:
        template = template_path.read_text(encoding="utf-8")
    else:
        template = DEFAULT_TEMPLATE

    skills = ", ".join(
        (config.profile.qualifications.skill_values() + config.profile.qualifications.software_values())[:6]
    ) or "meine bisherigen beruflichen Erfahrungen"
    exp = config.profile.qualifications.work_experience
    if exp:
        first = exp[0]
        label = first.label() if hasattr(first, "label") else str(first)
        experience_sentence = f"In meiner bisherigen Tätigkeit ({label}) habe ich relevante Erfahrungen gesammelt."
    else:
        experience_sentence = "Gern bringe ich meine bisherigen beruflichen Erfahrungen in Ihr Team ein."

    mapping = {
        "job_title": job.title,
        "company": job.company,
        "skills": skills,
        "experience_sentence": experience_sentence,
        "full_name": config.application.full_name or "[Ihr Name]",
        "first_name": config.application.first_name,
        "last_name": config.application.last_name,
    }

    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            # Keep unknown placeholders visible instead of crashing apply.
            return "{" + key + "}"

    try:
        return template.format_map(_Safe(mapping))
    except (ValueError, IndexError):
        # Malformed braces in a user template — fall back to default.
        return DEFAULT_TEMPLATE.format_map(_Safe(mapping))


def save_cover_letter(text: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
