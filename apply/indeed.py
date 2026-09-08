"""Indeed Quick Apply. Adapted from AutoApply (MIT)."""

from __future__ import annotations

import logging
from pathlib import Path

from apply.base import ApplyResult, BaseApplier
from core.config import ApplicationProfile
from core.models import Job

logger = logging.getLogger("jobhuntsaver")


class IndeedApplier(BaseApplier):
    def _do_apply(
        self,
        job: Job,
        resume_pdf_path: Path | None,
        cover_letter_text: str,
        profile: ApplicationProfile,
    ) -> ApplyResult:
        page = self.page
        logger.info("Indeed: applying to %s at %s", job.title, job.company)
        self._safe_goto(job.application_url or job.url)
        self._random_pause(1, 3)
        if self._detect_captcha():
            return ApplyResult(success=False, captcha_detected=True, error_message="CAPTCHA detected")
        apply_btn = self._wait_and_query(
            "button#indeedApplyButton, button[id*='indeedApply'], button[aria-label*='Apply now']",
            timeout=8000,
        )
        if not apply_btn:
            return ApplyResult(
                success=False,
                manual_required=True,
                needs_review=True,
                error_message="Indeed apply button not found / external ATS",
            )
        apply_btn.click()
        self._random_pause(2, 3)
        if "indeed.com" not in page.url:
            return ApplyResult(success=False, manual_required=True, needs_review=True, error_message="Redirected to external ATS")
        for _ in range(8):
            if self._detect_captcha():
                return ApplyResult(success=False, captcha_detected=True, error_message="CAPTCHA detected")
            self._safe_fill("input[name*='name'], input[id*='name']", profile.full_name)
            self._safe_fill("input[name*='email'], input[id*='email']", profile.email)
            self._safe_fill("input[name*='phone'], input[id*='phone']", profile.phone_full)
            if resume_pdf_path:
                self._safe_upload(resume_pdf_path, ["input[type='file']"])
            if self.dry_run or not self.submit:
                # Stop before final submit in review/dry-run
                submit = self._wait_and_query(
                    "button[aria-label*='Submit'], button[id*='submit']",
                    timeout=1500,
                )
                if submit:
                    return ApplyResult(success=True, dry_run_stopped=True, error_message="Stopped before Indeed submit")
            if self._safe_click("button[aria-label*='Submit'], button[id*='submit']", timeout=2000):
                if self.dry_run or not self.submit:
                    return ApplyResult(success=True, dry_run_stopped=True)
                self._random_pause(2, 4)
                return ApplyResult(success=True, submitted=True)
            if not self._safe_click(
                "button.ia-continueButton, button[aria-label*='Continue'], button[id*='continue']",
                timeout=2000,
            ):
                break
            self._random_pause(1, 2)
        return ApplyResult(success=False, needs_review=True, error_message="Could not complete Indeed application")
