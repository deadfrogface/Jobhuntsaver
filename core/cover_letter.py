"""Cover letter template rendering (no paid AI required)."""

from __future__ import annotations

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


def render_cover_letter(job: Job, config: AppConfig) -> str:
    template_path = Path(config.settings.cover_letter_template)
    if not template_path.is_absolute():
        template_path = config.root / template_path
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = DEFAULT_TEMPLATE

    skills = ", ".join(config.profile.qualifications.skills[:6]) or "meine bisherigen beruflichen Erfahrungen"
    exp = config.profile.qualifications.work_experience
    if exp:
        experience_sentence = f"In meiner bisherigen Tätigkeit ({exp[0]}) habe ich relevante Erfahrungen gesammelt."
    else:
        experience_sentence = "Gern bringe ich meine bisherigen beruflichen Erfahrungen in Ihr Team ein."

    return template.format(
        job_title=job.title,
        company=job.company,
        skills=skills,
        experience_sentence=experience_sentence,
        full_name=config.application.full_name or "[Ihr Name]",
        first_name=config.application.first_name,
        last_name=config.application.last_name,
    )


def save_cover_letter(text: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
