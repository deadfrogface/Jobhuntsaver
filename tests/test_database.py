"""Database and never-apply-twice tests."""

from pathlib import Path

from core.database import Database
from core.models import ApplicationRecord, Job, JobStatus


def test_db_roundtrip(tmp_path: Path):
    db = Database(tmp_path / "t.db")
    job = Job(id="abc", title="T", company="C", source="bundesagentur", match_score=80)
    db.upsert_job(job)
    got = db.get_job("abc")
    assert got is not None
    assert got.title == "T"
    assert got.match_score == 80


def test_never_apply_twice(tmp_path: Path):
    db = Database(tmp_path / "t.db")
    job = Job(id="j1", title="Sachbearbeiter", company="ACME", url="https://x/1", status=JobStatus.APPLIED.value)
    db.upsert_job(job)
    db.save_application(
        ApplicationRecord(job_id="j1", company="ACME", position="Sachbearbeiter", status=JobStatus.APPLIED.value)
    )
    twin = Job(id="j2", title="Sachbearbeiter", company="ACME", url="https://x/1")
    assert db.has_applied(twin) is True
    other = Job(id="j3", title="Andere Rolle", company="Other", url="https://y/2")
    assert db.has_applied(other) is False
