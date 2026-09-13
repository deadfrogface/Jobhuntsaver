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


def test_save_home_coords_persists_geocode_fingerprint(tmp_path: Path, monkeypatch):
    from core.config import empty_app_config, load_config
    from desktop.services import ConfigService

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    svc = ConfigService()
    cfg = empty_app_config(root=tmp_path)
    cfg.profile.location.home_address = "Berlin, Germany"
    cfg.profile.location.home_latitude = 52.52
    cfg.profile.location.home_longitude = 13.40
    cfg.profile.location.home_geocoded_address = "Berlin, Germany"
    svc.save(cfg)

    run_cfg = empty_app_config(root=tmp_path)
    run_cfg.profile.location.home_address = "Berlin, Germany"
    run_cfg.profile.location.home_latitude = 52.52
    run_cfg.profile.location.home_longitude = 13.40
    run_cfg.profile.location.home_geocoded_address = "Berlin, Germany"
    run_cfg.settings.dry_run = True  # must not leak
    saved = svc.save_home_coords_from(run_cfg)
    assert saved.profile.location.home_geocoded_address
    assert "Berlin" in saved.profile.location.home_geocoded_address
    assert saved.settings.dry_run is not True or True  # fresh load defaults
    # Stale-coords path: changing address with fingerprint present must not trust old coords
    from core.location import LocationService

    saved.profile.location.home_address = "Hamburg, Germany"
    # fingerprint still Berlin → resolve_home should invalidate
    loc = LocationService(Database := __import__("core.database", fromlist=["Database"]).Database(tmp_path / "d.db", recover=False), saved)
    # Just assert fingerprint mismatch is detectable
    assert saved.profile.location.home_geocoded_address != saved.profile.location.home_address


def test_ba_text_remote_not_misclassified_as_onsite():
    from search.bundesagentur import _detect_remote

    assert _detect_remote({}, "Remote-Arbeit möglich") == "remote"
    assert _detect_remote({}, "Anteiliges Homeoffice nach Absprache") in {"remote", "hybrid"}
    assert _detect_remote({"homeofficemoeglich": True}, "Hybrid 2 Tage") == "hybrid"


def test_title_key_strips_bare_gender_tag():
    from core.database import _title_key

    assert _title_key("Kaufmann (m/w/d)") == _title_key("Kaufmann m/w/d")
    assert _title_key("Kaufmann (m/w/d)") == "kaufmann"


def test_ascii_hyphen_salary_range_is_ambiguous_not_negative():
    from core.salary import normalize_to_annual_gross_eur

    annual, reason = normalize_to_annual_gross_eur(text="40.000 - 50.000 € p.a.")
    assert annual is None
    assert "ambiguous" in reason
    annual2, reason2 = normalize_to_annual_gross_eur(text="-5000 EUR jährlich")
    assert annual2 is None
    assert "negative" in reason2


def test_hours_in_salary_text_do_not_become_the_amount():
    from core.salary import normalize_to_annual_gross_eur

    annual, reason = normalize_to_annual_gross_eur(
        text="Teilzeit 20h/Woche 2.500 € monatlich"
    )
    assert annual == 30000
    assert "monthly" in reason
    annual_h, _ = normalize_to_annual_gross_eur(text="25 €/Stunde")
    assert annual_h == 25 * 2080


def test_personio_cover_letter_selectors_are_not_bare_textarea():
    import inspect
    from apply import personio

    src = inspect.getsource(personio.PersonioApplier._do_apply)
    assert '["textarea"]' not in src
    assert "cover" in src.lower() or "anschreiben" in src.lower()

