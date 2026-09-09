"""SAP SuccessFactors application adapter — conservative needs_review defaults."""

from __future__ import annotations

import logging
from pathlib import Path

from apply.base import ApplyResult, BaseApplier
from core.config import ApplicationProfile
from core.models import Job

logger = logging.getLogger("jobhuntsaver")

_SUBMIT_SEL = "button[type='submit'], button:has-text('Submit'), button:has-text('Senden')"


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
        self._fill_identity_fields(
            profile,
            first_name="input[id*='first'], input[name*='first']",
            last_name="input[id*='last'], input[name*='last']",
            resume_pdf_path=resume_pdf_path,
        )

        # Many SF portals require login / complex multi-page flows
        if self.page.query_selector("input[type='password'], text=Sign In, text=Anmelden"):
            return ApplyResult(
                success=False,
                login_required=True,
                needs_review=True,
                error_message="SuccessFactors login required",
            )

        # Always use the central submit guard when a submit control is present.
        if self._wait_and_query(_SUBMIT_SEL, timeout=2000):
            result = self._maybe_submit(_SUBMIT_SEL)
            if result.dry_run_stopped or result.submitted:
                result.needs_review = True
                if not result.error_message:
                    result.error_message = "SuccessFactors — review recommended"
                return result
            return result

        return ApplyResult(
            success=False,
            needs_review=True,
            manual_required=True,
            error_message="SuccessFactors auto-submit not reliable — needs_review",
        )
