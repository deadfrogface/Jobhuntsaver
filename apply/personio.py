"""Personio careers application adapter (Germany-focused)."""

from __future__ import annotations

import logging
from pathlib import Path

from apply.base import ApplyResult, BaseApplier
from core.config import ApplicationProfile
from core.models import Job

logger = logging.getLogger("jobhuntsaver")


class PersonioApplier(BaseApplier):
    def _do_apply(
        self,
        job: Job,
        resume_pdf_path: Path | None,
        cover_letter_text: str,
        profile: ApplicationProfile,
    ) -> ApplyResult:
        logger.info("Personio: applying to %s at %s", job.title, job.company)
        self._safe_goto(job.application_url or job.url)
        self._random_pause(1, 3)
        if self._detect_captcha():
            return ApplyResult(success=False, captcha_detected=True, error_message="CAPTCHA detected")

        self._safe_click("a:has-text('Jetzt bewerben'), button:has-text('Jetzt bewerben'), a:has-text('Apply'), button:has-text('Apply')", timeout=4000)
        self._random_pause(1, 2)

        self._safe_fill("input[name*='first'], input[id*='first']", profile.first_name)
        self._safe_fill("input[name*='last'], input[id*='last']", profile.last_name)
        self._safe_fill("input[type='email']", profile.email)
        self._safe_fill("input[type='tel'], input[name*='phone']", profile.phone_full)
        if resume_pdf_path:
            uploaded = self._safe_upload(resume_pdf_path, ["input[type='file']"])
            if not uploaded:
                return ApplyResult(success=False, needs_review=True, error_message="Personio CV upload failed")
        if cover_letter_text:
            ta = self.page.query_selector("textarea")
            if ta and ta.is_visible():
                ta.fill(cover_letter_text)

        unknown = []
        for el in self.page.query_selector_all("input[required], textarea[required], select[required]"):
            name = (el.get_attribute("name") or el.get_attribute("id") or "field").lower()
            if any(k in name for k in ("first", "last", "email", "phone", "file", "cv", "resume")):
                continue
            try:
                if el.input_value():
                    continue
            except Exception:
                pass
            answered = False
            for key, val in profile.answers.items():
                if key.lower() in name and val:
                    self._safe_fill(f"[name='{el.get_attribute('name')}']", val)
                    answered = True
                    break
            if not answered:
                unknown.append(name)
        if unknown:
            return ApplyResult(
                success=False,
                needs_review=True,
                error_message=f"Unknown Personio fields: {', '.join(unknown[:5])}",
            )
        return self._maybe_submit("button[type='submit'], input[type='submit'], button:has-text('Senden'), button:has-text('Submit')")
