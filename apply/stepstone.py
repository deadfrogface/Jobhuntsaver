"""StepStone native application adapter.

If StepStone redirects to an external ATS, ApplicationManager should use ATSDetector.
"""

from __future__ import annotations

import logging
from pathlib import Path

from apply.base import ApplyResult, BaseApplier
from apply.detector import ATSDetector
from core.config import ApplicationProfile
from core.models import Job

logger = logging.getLogger("jobhuntsaver")


class StepstoneApplier(BaseApplier):
    def _do_apply(
        self,
        job: Job,
        resume_pdf_path: Path | None,
        cover_letter_text: str,
        profile: ApplicationProfile,
    ) -> ApplyResult:
        logger.info("StepStone: applying to %s at %s", job.title, job.company)
        self._safe_goto(job.application_url or job.url)
        self._random_pause(1, 3)
        if self._detect_captcha():
            return ApplyResult(success=False, captcha_detected=True, error_message="CAPTCHA detected")

        # Detect redirect to external ATS
        ats = ATSDetector.detect(self.page.url)
        if ats not in ("stepstone", "unknown"):
            return ApplyResult(
                success=False,
                manual_required=True,
                needs_review=True,
                error_message=f"StepStone redirected to external ATS: {ats}",
            )

        self._safe_click("a:has-text('Jetzt bewerben'), button:has-text('Jetzt bewerben')", timeout=4000)
        self._random_pause(1, 2)
        self._fill_identity_fields(
            profile,
            first_name="input[name*='first'], input[id*='firstName']",
            last_name="input[name*='last'], input[id*='lastName']",
            resume_pdf_path=resume_pdf_path,
        )
        if cover_letter_text:
            ta = self.page.query_selector("textarea")
            if ta and ta.is_visible():
                ta.fill(cover_letter_text)
        return self._maybe_submit("button[type='submit'], button:has-text('Bewerbung absenden')")
