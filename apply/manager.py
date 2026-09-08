"""Application manager — safety checks and adapter dispatch."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from apply.ashby import AshbyApplier
from apply.base import ApplyResult, BaseApplier
from apply.detector import ATSDetector
from apply.greenhouse import GreenhouseApplier
from apply.indeed import IndeedApplier
from apply.lever import LeverApplier
from apply.linkedin import LinkedInApplier
from apply.personio import PersonioApplier
from apply.smartrecruiters import SmartRecruitersApplier
from apply.stepstone import StepstoneApplier
from apply.successfactors import SuccessFactorsApplier
from apply.workday import WorkdayApplier
from core.config import AppConfig
from core.cover_letter import render_cover_letter, save_cover_letter
from core.database import Database
from core.models import ApplicationRecord, Job, JobStatus, OperatingMode, utc_now_iso

logger = logging.getLogger("jobhuntsaver")

APPLIERS: dict[str, type[BaseApplier]] = {
    "greenhouse": GreenhouseApplier,
    "lever": LeverApplier,
    "ashby": AshbyApplier,
    "indeed": IndeedApplier,
    "linkedin": LinkedInApplier,
    "workday": WorkdayApplier,
    "personio": PersonioApplier,
    "stepstone": StepstoneApplier,
    "smartrecruiters": SmartRecruitersApplier,
    "successfactors": SuccessFactorsApplier,
}


class ApplicationManager:
    def __init__(self, config: AppConfig, db: Database, page=None) -> None:
        self.config = config
        self.db = db
        self.page = page
        self.applied_this_run = 0
        self.failed_this_run = 0

    def can_auto_apply(self, job: Job) -> tuple[bool, str]:
        settings = self.config.settings
        if job.match_score < settings.minimum_match_for_auto_apply:
            return False, f"score {job.match_score} < {settings.minimum_match_for_auto_apply}"
        if self.db.has_applied(job):
            return False, "already applied (safety)"
        if self.applied_this_run >= settings.max_applications_per_run:
            return False, "max applications per run reached"
        if self.db.count_applications_today() >= settings.max_applications_per_day:
            return False, "max applications per day reached"
        if self.failed_this_run >= settings.max_failed_applications_per_run:
            return False, "max failed applications per run reached"
        app = self.config.application
        missing = [f for f, v in {
            "first_name": app.first_name,
            "last_name": app.last_name,
            "email": app.email,
            "phone": app.phone,
            "cv_path": app.cv_path,
        }.items() if not v]
        if missing:
            return False, f"missing profile fields: {', '.join(missing)}"
        ats = job.ats_type or ATSDetector.detect(job.application_url or job.url)
        if ats == "unknown" or ats not in APPLIERS:
            return False, f"ATS unsupported: {ats}"
        return True, "ok"

    def prepare_and_apply(self, job: Job, *, force_submit: bool | None = None) -> ApplyResult:
        settings = self.config.settings
        mode = settings.mode
        submit = False
        if force_submit is not None:
            submit = force_submit
        elif mode == OperatingMode.FULLY_AUTOMATIC.value and not settings.dry_run:
            submit = True

        allowed, reason = self.can_auto_apply(job)
        if not allowed and mode == OperatingMode.FULLY_AUTOMATIC.value:
            job.status = JobStatus.NEEDS_REVIEW.value
            job.rejection_reasons = list({*job.rejection_reasons, reason})
            self.db.upsert_job(job)
            return ApplyResult(success=False, needs_review=True, error_message=reason)

        ats = ATSDetector.detect(job.application_url or job.url)
        job.ats_type = ats
        if ats == "unknown" or ats not in APPLIERS:
            job.status = JobStatus.NEEDS_REVIEW.value
            self.db.upsert_job(job)
            return ApplyResult(
                success=False,
                needs_review=True,
                manual_required=True,
                error_message=f"Unsupported ATS: {ats}",
            )

        if self.page is None:
            return ApplyResult(success=False, error_message="Browser page not available")

        # Final never-apply-twice check
        if self.db.has_applied(job):
            return ApplyResult(success=False, error_message="already applied (safety)")

        cover = render_cover_letter(job, self.config)
        cover_path = self.config.root / "private" / "cover_letters" / f"{job.id}.txt"
        save_cover_letter(cover, cover_path)
        cv_path = Path(self.config.application.cv_path) if self.config.application.cv_path else None
        if cv_path and not cv_path.is_absolute():
            cv_path = self.config.root / cv_path

        job.status = JobStatus.APPLYING.value
        self.db.upsert_job(job)

        applier_cls = APPLIERS[ats]
        applier = applier_cls(self.page, dry_run=settings.dry_run or not submit, submit=submit)
        result = applier.apply(job, cv_path if cv_path and cv_path.exists() else None, cover, self.config.application)

        status = JobStatus.NEEDS_REVIEW.value
        if result.captcha_detected:
            status = JobStatus.CAPTCHA.value
            self.failed_this_run += 1
        elif result.needs_review or result.manual_required or result.dry_run_stopped:
            status = JobStatus.NEEDS_REVIEW.value
        elif result.success and result.submitted:
            status = JobStatus.APPLIED.value
            self.applied_this_run += 1
        elif result.success and not result.submitted:
            status = JobStatus.NEEDS_REVIEW.value
        else:
            status = JobStatus.FAILED.value
            self.failed_this_run += 1

        job.status = status
        self.db.upsert_job(job)
        self.db.save_application(
            ApplicationRecord(
                job_id=job.id,
                company=job.company,
                position=job.title,
                application_date=utc_now_iso(),
                platform=ats,
                status=status,
                cv_used=str(cv_path or ""),
                cover_letter_used=str(cover_path),
                result="submitted" if result.submitted else ("dry_run" if result.dry_run_stopped else "stopped"),
                error_message=result.error_message or "",
            )
        )
        time.sleep(max(1, settings.delay_between_applications_seconds))
        return result
