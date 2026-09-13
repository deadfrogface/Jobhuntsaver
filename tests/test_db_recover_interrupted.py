"""Crash mid-apply / mid-search must heal only when recover=True."""

from __future__ import annotations

from pathlib import Path

from core.database import Database
from core.models import Job, JobStatus


def test_applying_job_becomes_needs_review_on_recover(tmp_path: Path):
    db_path = tmp_path / "jobs.db"
    db = Database(db_path)
    job = Job(
        id="j-apply",
        source="test",
        title="Buchhalter",
        company="ACME",
        url="https://example.com/1",
        status=JobStatus.APPLYING.value,
    )
    db.upsert_job(job)
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO search_runs (id, started_at, finished_at, status, stats_json) VALUES (?,?,?,?,?)",
            ("run1", "2026-01-01T00:00:00+00:00", "", "running", "{}"),
        )
    # Explicit recover=True heals crash leftovers (app/pipeline start).
    db2 = Database(db_path, recover=True)
    loaded = db2.get_job("j-apply")
    assert loaded is not None
    assert loaded.status == JobStatus.NEEDS_REVIEW.value
    with db2.connection() as conn:
        run = conn.execute(
            "SELECT status, finished_at FROM search_runs WHERE id=?", ("run1",)
        ).fetchone()
    assert run[0] == "interrupted"
    assert run[1]


def test_second_database_keeps_live_running_search(tmp_path: Path):
    """GUI page opens must not interrupt an in-progress search_run."""
    db_path = tmp_path / "jobs.db"
    db = Database(db_path)
    rid = db.start_search_run("live-run")
    assert rid == "live-run"

    db2 = Database(db_path)  # recover=False default
    with db2.connection() as conn:
        run = conn.execute(
            "SELECT status, finished_at FROM search_runs WHERE id=?", ("live-run",)
        ).fetchone()
    assert run[0] == "running"
    assert run[1] == ""


def test_applying_job_survives_second_database_during_live_session(tmp_path: Path):
    """Mid-apply job must survive GUI Database() opens while pipeline is live."""
    db_path = tmp_path / "jobs.db"
    db = Database(db_path)
    db.start_search_run("live-apply")
    job = Job(
        id="j-live-apply",
        source="test",
        title="Buchhalter",
        company="ACME",
        url="https://example.com/live",
        status=JobStatus.APPLYING.value,
    )
    db.upsert_job(job)

    db2 = Database(db_path)  # recover=False default
    loaded = db2.get_job("j-live-apply")
    assert loaded is not None
    assert loaded.status == JobStatus.APPLYING.value
    with db2.connection() as conn:
        run = conn.execute(
            "SELECT status FROM search_runs WHERE id=?", ("live-apply",)
        ).fetchone()
    assert run[0] == "running"


def test_recover_ignores_non_running_empty_finished_at(tmp_path: Path):
    """Empty finished_at alone must not mark a finished run interrupted."""
    db_path = tmp_path / "jobs.db"
    db = Database(db_path)
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO search_runs (id, started_at, finished_at, status, stats_json) VALUES (?,?,?,?,?)",
            ("done-empty", "2026-01-01T00:00:00+00:00", "", "ok", "{}"),
        )
    Database(db_path, recover=True)
    with Database(db_path).connection() as conn:
        run = conn.execute(
            "SELECT status FROM search_runs WHERE id=?", ("done-empty",)
        ).fetchone()
    assert run[0] == "ok"
