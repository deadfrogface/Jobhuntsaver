"""Workday ATS application automation. Adapted from AutoApply (MIT), simplified for dry-run safety."""

from __future__ import annotations

import logging
from pathlib import Path

from apply.base import ApplyResult, BaseApplier
from core.config import ApplicationProfile
from core.models import Job

logger = logging.getLogger("jobhuntsaver")


class WorkdayApplier(BaseApplier):
    def _do_apply(
        self,
        job: Job,
        resume_pdf_path: Path | None,
        cover_letter_text: str,
        profile: ApplicationProfile,
    ) -> ApplyResult:
        logger.info("Workday: applying to %s at %s", job.title, job.company)
        self._safe_goto(job.application_url or job.url)
        self._random_pause(2, 4)
        if self._detect_captcha():
            return ApplyResult(success=False, captcha_detected=True, error_message="CAPTCHA detected")

        self._safe_click(
            "a[data-automation-id='jobPostingApplyButton'], button[data-automation-id='adventureButton'], a:has-text('Apply')",
            timeout=5000,
        )
        self._random_pause(2, 3)

        # Create account / sign in walls are common
        if self.page.query_selector("input[data-automation-id='email'], text=Sign In"):
            # Try guest apply if available
            if not self._safe_click("button:has-text('Apply Manually'), a:has-text('Apply Manually')", timeout=3000):
                return ApplyResult(
                    success=False,
                    login_required=True,
                    needs_review=True,
                    error_message="Workday login required",
                )

        self._fill_identity_fields(
            profile,
            first_name="input[data-automation-id='legalNameSection_firstName'], input[name*='firstName']",
            last_name="input[data-automation-id='legalNameSection_lastName'], input[name*='lastName']",
            email="input[data-automation-id='email'], input[type='email']",
            phone="input[data-automation-id='phone-number'], input[type='tel']",
            resume_pdf_path=resume_pdf_path,
        )
        if cover_letter_text:
            ta = self.page.query_selector("textarea")
            if ta and ta.is_visible():
                ta.fill(cover_letter_text)

        # Multi-step: advance carefully; stop before final submit in dry_run
        for _ in range(6):
            if self._detect_captcha():
                return ApplyResult(success=False, captcha_detected=True, error_message="CAPTCHA detected")
            submit = self._wait_and_query(
                "button[data-automation-id='pageFooterNextButton']:has-text('Submit'), button:has-text('Submit')",
                timeout=1500,
            )
            if submit:
                return self._maybe_submit(
                    "button[data-automation-id='pageFooterNextButton']:has-text('Submit'), button:has-text('Submit')"
                )
            if not self._safe_click(
                "button[data-automation-id='pageFooterNextButton'], button:has-text('Next'), button:has-text('Continue')",
                timeout=2500,
            ):
                break
            self._random_pause(1, 2)

        return ApplyResult(success=False, needs_review=True, manual_required=True, error_message="Workday form incomplete")
