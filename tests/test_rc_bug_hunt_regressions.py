"""Regression guards for RC adversarial bug hunt."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import patch


def test_frozen_shutdown_print_never_crashes_on_closed_stdout():
    from desktop.services.shutdown import ApplicationShutdownManager

    mgr = ApplicationShutdownManager()
    closed = io.StringIO()
    closed.close()
    with patch.object(sys, "frozen", True, create=True), patch.object(sys, "stdout", closed):
        mgr._log_step("rc-shutdown-probe")


def test_soft_dedup_requires_company_and_place():
    from core.deduplicator import deduplicate, is_likely_same_job
    from core.models import Job

    a = Job(
        id="1",
        source="indeed",
        title="Sachbearbeiter",
        company="",
        city="",
        url="https://a.example/1",
    )
    b = Job(
        id="2",
        source="stepstone",
        title="Sachbearbeiter",
        company="",
        city="",
        url="https://b.example/2",
    )
    assert is_likely_same_job(a, b) is False
    out = deduplicate([a, b])
    assert all(not j.duplicate_of for j in out)


def test_soft_dedup_still_merges_strong_fingerprints():
    from core.deduplicator import deduplicate
    from core.models import Job

    a = Job(
        id="1",
        source="indeed",
        title="Sachbearbeiter",
        company="Acme GmbH",
        city="Berlin",
        url="https://a.example/1",
    )
    b = Job(
        id="2",
        source="stepstone",
        title="Sachbearbeiter",
        company="Acme GmbH",
        city="Berlin",
        url="https://b.example/2",
    )
    out = deduplicate([a, b])
    assert sum(1 for j in out if j.duplicate_of) == 1


def test_empty_queries_finish_search_run(tmp_path: Path):
    from app.main import run_pipeline
    from core.config import empty_app_config
    from core.database import Database

    cfg = empty_app_config(root=tmp_path)
    cfg.settings.database_path = "data/jobs.db"
    cfg.settings.logs_dir = "logs"
    (tmp_path / "data").mkdir()
    (tmp_path / "logs").mkdir()
    cfg.profile.jobs.desired_titles = []
    cfg.profile.location.home_address = ""
    cfg.profile.location.allow_remote_germany = False

    stats = run_pipeline(cfg, mode="search_only")
    assert stats.get("config_error") == "empty_queries"

    db = Database(cfg.db_path, recover=False)
    with db.connection() as conn:
        rows = list(conn.execute("SELECT status, finished_at FROM search_runs"))
    assert rows, "search_runs row must exist"
    assert rows[0]["status"] != "running"
    assert rows[0]["finished_at"]


def test_ats_rejects_marketing_and_profile_urls():
    from apply.detector import ATSDetector

    assert ATSDetector.detect("https://www.workday.com/en-us/company.html") == "unknown"
    assert ATSDetector.detect("https://www.linkedin.com/in/someone") == "unknown"
    assert ATSDetector.detect("https://example.com/?utm=greenhouse.io") == "unknown"
    assert ATSDetector.detect("https://boards.greenhouse.io/acme/jobs/123") == "greenhouse"
    assert ATSDetector.detect("https://company.myworkdayjobs.com/en-US/careers/job/1") == "workday"


def test_atomic_yaml_save_roundtrip(tmp_path: Path):
    from core.config import empty_app_config, load_config, save_config

    cfg = empty_app_config(root=tmp_path)
    cfg.profile.jobs.desired_titles = ["Sachbearbeiter"]
    cfg.application.first_name = "Max"
    profile = tmp_path / "config" / "profile.yaml"
    application = tmp_path / "config" / "application_profile.yaml"
    settings = tmp_path / "config" / "settings.yaml"
    save_config(cfg, profile_path=profile, application_path=application, settings_path=settings)
    assert "Sachbearbeiter" in profile.read_text(encoding="utf-8")
    loaded = load_config(
        profile_path=profile,
        application_path=application,
        settings_path=settings,
        root=tmp_path,
    )
    assert loaded.profile.jobs.desired_titles == ["Sachbearbeiter"]
    assert loaded.application.first_name == "Max"


def test_salary_zero_text_is_unknown_not_zero():
    from core.salary import normalize_to_annual_gross_eur

    val, reason = normalize_to_annual_gross_eur(text="0 EUR")
    assert val is None
    assert "non-positive" in reason


def test_compound_ausbildung_berufserfahrung_is_heading():
    from core.cv_sections import is_heading

    assert is_heading("Ausbildung und Berufserfahrung") is not None


def test_bare_cefr_c1_not_treated_as_driving_class():
    from core.cv_parser import normalize_driving_license

    assert normalize_driving_license("C1") == []
    assert normalize_driving_license("Klasse C1") == ["C1"]
    assert normalize_driving_license("B, C1") == ["B", "C1"]


def test_has_applied_survives_url_and_title_drift(tmp_path: Path):
    from core.database import Database
    from core.models import ApplicationRecord, Job, JobStatus

    db = Database(tmp_path / "jobs.db", recover=False)
    applied = Job(
        id="job1",
        source="indeed",
        title="Sachbearbeiter (m/w/d)",
        company="Musterfirma GmbH",
        city="Berlin",
        url="https://de.indeed.com/viewjob?jk=abc123&from=serp",
        status=JobStatus.APPLIED.value,
    )
    db.upsert_job(applied)
    db.save_application(
        ApplicationRecord(
            job_id="job1",
            company=applied.company,
            position=applied.title,
            status="applied",
            result="submitted",
        )
    )
    drift = Job(
        id="job2",
        source="indeed",
        title="Sachbearbeiter",
        company="Musterfirma",
        city="Berlin",
        url="https://de.indeed.com/viewjob?jk=abc123&utm_source=share",
    )
    assert db.has_applied(drift) is True

    # Soft-dedup loser re-upsert must not wipe applied status.
    wipe = Job(
        id="job1",
        source="indeed",
        title="Sachbearbeiter (m/w/d)",
        company="Musterfirma GmbH",
        city="Berlin",
        url="https://de.indeed.com/viewjob?jk=abc123",
        status=JobStatus.NEW.value,
    )
    db.upsert_job(wipe)
    assert db.get_job("job1").status == JobStatus.APPLIED.value


def test_salary_tvoed_weekly_and_negative_are_unknown():
    from core.salary import normalize_to_annual_gross_eur as n

    assert n(text="TVÖD E9")[0] is None
    weekly, how = n(text="1.500 EUR / Woche")
    assert weekly == 78000
    assert "weekly" in how
    assert n(text="-5000 EUR monatlich")[0] is None


def test_daily_quota_ignores_dry_run_rows(tmp_path: Path):
    from core.database import Database
    from core.models import ApplicationRecord, Job, JobStatus

    db = Database(tmp_path / "jobs.db", recover=False)
    for jid, company in (("a", "A"), ("b", "B")):
        db.upsert_job(
            Job(id=jid, source="t", title="P", company=company, status=JobStatus.NEW.value)
        )
    db.save_application(
        ApplicationRecord(job_id="a", company="A", position="P", status="dry_run", result="preview")
    )
    db.save_application(
        ApplicationRecord(job_id="b", company="B", position="P", status="applied", result="submitted")
    )
    assert db.count_applications_today() == 1


def test_sync_application_summaries_keeps_manual_origin():
    from core.config import (
        ApplicationProfile,
        EducationEntry,
        ExperienceEntry,
        QualificationsConfig,
    )
    from desktop.services.profile_merge import (
        SOURCE_MANUAL,
        set_field_origin,
        sync_application_summaries,
    )

    app = ApplicationProfile(education="Manuell behalten", languages="Manuell DE")
    set_field_origin(app, "education", SOURCE_MANUAL)
    set_field_origin(app, "languages", SOURCE_MANUAL)
    quals = QualificationsConfig(
        education=[EducationEntry(qualification="Bachelor Informatik")],
        work_experience=[ExperienceEntry(title="Dev", company="X")],
    )
    sync_application_summaries(app, quals)
    assert app.education == "Manuell behalten"
    assert app.languages == "Manuell DE"
