"""SAP SuccessFactors application adapter — conservative needs_review defaults."""

from __future__ import annotations

import logging
from pathlib import Path

from apply.base import ApplyResult, BaseApplier
from core.config import ApplicationProfile
from core.models import Job

logger = logging.getLogger("jobhuntsaver")


class SuccessFactorsApplier(BaseApplier):
    def _do_apply(
        self,
        job: Job,
        resume_pdf_path: Path | None,
        cover_letter_text: str,
        profile: ApplicationProfile,
    ) -> ApplyResult:
        logger.info("SuccessFactors: opening %s at %s", job.title, job.company)
        self._safe_goto(job.application_url or job.url)
        self._random_pause(2, 4)
        if self._detect_captcha():
            return ApplyResult(success=False, captcha_detected=True, error_message="CAPTCHA detected")

        # SuccessFactors UIs vary widely — fill what we can, prefer needs_review
        self._safe_fill("input[id*='first'], input[name*='first']", profile.first_name)
        self._safe_fill("input[id*='last'], input[name*='last']", profile.last_name)
        self._safe_fill("input[type='email']", profile.email)
        self._safe_fill("input[type='tel']", profile.phone_full)
        if resume_pdf_path:
            self._safe_upload(resume_pdf_path, ["input[type='file']"])

        # Many SF portals require login / complex multi-page flows
        if self.page.query_selector("input[type='password'], text=Sign In, text=Anmelden"):
            return ApplyResult(
                success=False,
                login_required=True,
                needs_review=True,
                error_message="SuccessFactors login required",
            )

        if self.dry_run or not self.submit:
            return self._maybe_submit("button[type='submit'], button:has-text('Submit')")
        return ApplyResult(
            success=False,
            needs_review=True,
            manual_required=True,
            error_message="SuccessFactors auto-submit not reliable — needs_review",
        )
