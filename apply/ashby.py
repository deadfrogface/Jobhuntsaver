"""Ashby ATS application automation. Adapted from AutoApply (MIT)."""

from __future__ import annotations

import logging
from pathlib import Path

from apply.base import ApplyResult, BaseApplier
from core.config import ApplicationProfile
from core.models import Job

logger = logging.getLogger("jobhuntsaver")


class AshbyApplier(BaseApplier):
    def _do_apply(
        self,
        job: Job,
        resume_pdf_path: Path | None,
        cover_letter_text: str,
        profile: ApplicationProfile,
    ) -> ApplyResult:
        logger.info("Ashby: applying to %s at %s", job.title, job.company)
        self._safe_goto(job.application_url or job.url)
        self._random_pause(1, 3)
        if self._detect_captcha():
            return ApplyResult(success=False, captcha_detected=True, error_message="CAPTCHA detected")
        self._safe_click('a:has-text("Apply"), button:has-text("Apply")', timeout=3000)
        self._random_pause(1, 2)
        self._safe_fill('input[name*="firstName"], input[name*="first_name"]', profile.first_name)
        self._safe_fill('input[name*="lastName"], input[name*="last_name"]', profile.last_name)
        self._safe_fill('input[name="name"]', profile.full_name)
        self._safe_fill('input[type="email"], input[name*="email"]', profile.email)
        self._safe_fill('input[type="tel"], input[name*="phone"]', profile.phone_full)
        if profile.linkedin_url:
            self._safe_fill('input[name*="linkedin"], input[placeholder*="LinkedIn"]', profile.linkedin_url)
        if resume_pdf_path:
            self._safe_upload(resume_pdf_path, ['input[type="file"]'])
        if cover_letter_text:
            ta = self.page.query_selector('textarea[name*="cover"], textarea[placeholder*="cover"]')
            if ta and ta.is_visible():
                ta.fill(cover_letter_text)
        # Custom questions: only fill known answers; otherwise needs_review
        unknown = []
        for label in self.page.query_selector_all("label"):
            try:
                label_text = label.inner_text().strip().lower()
            except Exception:
                continue
            matched = False
            for key, value in profile.answers.items():
                if key.lower().replace("_", " ") in label_text and value:
                    label_for = label.get_attribute("for")
                    if label_for:
                        self._safe_fill(f"#{label_for}", value)
                        matched = True
                        break
            if not matched and "*" in label_text:
                if not any(x in label_text for x in ("name", "email", "phone", "resume")):
                    unknown.append(label_text[:80])
        if unknown:
            return ApplyResult(
                success=False,
                needs_review=True,
                error_message=f"Unknown questions: {', '.join(unknown[:3])}",
            )
        return self._maybe_submit('button[type="submit"]')
