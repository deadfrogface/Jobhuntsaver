"""Crash mid-apply / mid-search must heal on next Database open."""

from __future__ import annotations

from pathlib import Path

from core.database import Database
from core.models import Job, JobStatus


def test_applying_job_becomes_needs_review_on_reopen(tmp_path: Path):
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
    # Re-open triggers recover_interrupted_state
    db2 = Database(db_path)
    loaded = db2.get_job("j-apply") if hasattr(db2, "get_job") else None
    if loaded is None:
        with db2.connection() as conn:
            row = conn.execute("SELECT status FROM jobs WHERE id=?", ("j-apply",)).fetchone()
            status = row[0]
            run = conn.execute("SELECT status, finished_at FROM search_runs WHERE id=?", ("run1",)).fetchone()
    else:
        status = loaded.status
        with db2.connection() as conn:
            run = conn.execute("SELECT status, finished_at FROM search_runs WHERE id=?", ("run1",)).fetchone()
    assert status == JobStatus.NEEDS_REVIEW.value
    assert run[0] == "interrupted"
    assert run[1]
