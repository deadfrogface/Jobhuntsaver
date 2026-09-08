"""Greenhouse ATS application automation.

Adapted from AutoApply bot/apply/greenhouse.py (MIT).
"""

from __future__ import annotations

import logging
from pathlib import Path

from apply.base import ApplyResult, BaseApplier
from core.config import ApplicationProfile
from core.models import Job

logger = logging.getLogger("jobhuntsaver")


class GreenhouseApplier(BaseApplier):
    def _do_apply(
        self,
        job: Job,
        resume_pdf_path: Path | None,
        cover_letter_text: str,
        profile: ApplicationProfile,
    ) -> ApplyResult:
        logger.info("Greenhouse: applying to %s at %s", job.title, job.company)
        self._safe_goto(job.application_url or job.url)
        self._random_pause(1, 3)

        if self._detect_captcha():
            return ApplyResult(success=False, captcha_detected=True, error_message="CAPTCHA detected")

        self._safe_click(
            "a#apply_button, a[href*='#app'], button[id*='apply'], a.btn[href*='apply']",
            timeout=3000,
        )
        self._random_pause(1, 2)
        self._fill_form_fields(profile)
        if resume_pdf_path:
            self._safe_upload(
                resume_pdf_path,
                [
                    "input[type='file'][name*='resume']",
                    "input[type='file'][id*='resume']",
                    "input[type='file']",
                ],
            )
        self._fill_cover_letter(cover_letter_text)
        unknown = self._unknown_required_fields(profile)
        if unknown:
            return ApplyResult(
                success=False,
                needs_review=True,
                manual_required=True,
                error_message=f"Unknown required fields: {', '.join(unknown)}",
            )
        return self._maybe_submit(
            "input[type='submit']#submit_app, input[type='submit'][value*='Submit'], "
            "button[type='submit'], input#submit_app"
        )

    def _fill_form_fields(self, profile: ApplicationProfile) -> None:
        field_map = {
            "#first_name, input[name*='first_name']": profile.first_name,
            "#last_name, input[name*='last_name']": profile.last_name,
            "#email, input[name*='email']": profile.email,
            "#phone, input[name*='phone']": profile.phone_full,
        }
        for selector, value in field_map.items():
            self._safe_fill(selector, value)
        if profile.linkedin_url:
            self._safe_fill(
                "input[name*='linkedin'], input[id*='linkedin']",
                profile.linkedin_url,
            )

    def _fill_cover_letter(self, text: str) -> None:
        if not text:
            return
        textarea = self.page.query_selector(
            "textarea[name*='cover_letter'], textarea[id*='cover_letter'], #cover_letter"
        )
        if textarea and textarea.is_visible():
            try:
                if not textarea.input_value():
                    textarea.fill(text)
            except Exception:
                textarea.fill(text)

    def _unknown_required_fields(self, profile: ApplicationProfile) -> list[str]:
        unknown: list[str] = []
        for el in self.page.query_selector_all("input[required], textarea[required], select[required]"):
            try:
                name = (el.get_attribute("name") or el.get_attribute("id") or "").lower()
                if not name:
                    continue
                if any(k in name for k in ("first", "last", "email", "phone", "resume", "cover")):
                    continue
                # known custom answers?
                answered = False
                for key, val in profile.answers.items():
                    if key.lower() in name and val:
                        self._safe_fill(f"[name='{el.get_attribute('name')}']", val)
                        answered = True
                        break
                if not answered:
                    try:
                        if el.input_value():
                            continue
                    except Exception:
                        pass
                    unknown.append(name)
            except Exception:
                continue
        return unknown
