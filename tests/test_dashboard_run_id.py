"""Dashboard this_run counters are scoped to the latest run_id."""

from __future__ import annotations

from pathlib import Path

from core.database import Database
from core.models import Job


def test_this_run_only_one_run_id(tmp_path: Path):
    db = Database(tmp_path / "jobs.db")
    run_a = db.start_search_run("run_a")
    run_b = db.start_search_run("run_b")
    assert run_a == "run_a" and run_b == "run_b"

    db.upsert_job(
        Job(id="a1", source="t", source_job_id="1", title="A", company="C", run_id="run_a")
    )
    db.upsert_job(
        Job(id="a2", source="t", source_job_id="2", title="B", company="C", run_id="run_a")
    )
    db.upsert_job(
        Job(id="b1", source="t", source_job_id="3", title="C", company="C", run_id="run_b")
    )

    # Latest run is run_b — this_run must not include prior run jobs.
    assert db.latest_run_id() == "run_b"
    stats = db.dashboard_stats()
    assert stats["this_run"] == 1
    assert db.dashboard_stats(run_id="run_a")["this_run"] == 2
    assert db.dashboard_stats(run_id="run_b")["this_run"] == 1


def test_previous_runs_do_not_leak_into_this_run(tmp_path: Path):
    db = Database(tmp_path / "jobs.db")
    db.start_search_run("old")
    for i in range(5):
        db.upsert_job(
            Job(
                id=f"old{i}",
                source="t",
                source_job_id=str(i),
                title=f"T{i}",
                company="C",
                run_id="old",
            )
        )
    db.start_search_run("new")
    db.upsert_job(
        Job(id="new1", source="t", source_job_id="n1", title="N", company="C", run_id="new")
    )
    assert db.dashboard_stats()["this_run"] == 1
    assert db.dashboard_stats()["total_jobs"] == 6


def test_reset_zeros_this_run(tmp_path: Path):
    db = Database(tmp_path / "jobs.db")
    rid = db.start_search_run()
    db.upsert_job(Job(id="j1", source="t", source_job_id="1", title="T", company="C", run_id=rid))
    assert db.dashboard_stats()["this_run"] == 1
    db.clear_job_data(clear_applications=True, clear_source_status=True, clear_search_runs=True)
    assert db.dashboard_stats()["this_run"] == 0
    assert db.dashboard_stats()["total_jobs"] == 0
    assert db.latest_run_id() is None


def test_fresh_empty_this_run(tmp_path: Path):
    db = Database(tmp_path / "fresh.db")
    stats = db.dashboard_stats()
    assert stats["this_run"] == 0
    assert stats["total_jobs"] == 0
