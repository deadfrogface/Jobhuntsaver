"""CI helper: seed jobs under isolated LOCALAPPDATA, reset job data, keep profile."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    # LOCALAPPDATA must already point at an isolated CI temp directory.
    from core.database import Database
    from core.models import Job, JobStatus
    from desktop.services import ConfigService

    svc = ConfigService()
    cfg = svc.load()
    cfg.application.first_name = "Ada"
    cfg.application.last_name = "Lovelace"
    cfg.application.email = "ada@example.com"
    svc.save(cfg)

    db = Database(cfg.db_path)
    rid = db.start_search_run()
    db.upsert_job(
        Job(
            id="seed-1",
            source="test",
            title="Seed",
            company="Co",
            run_id=rid,
            status=JobStatus.NEEDS_REVIEW.value,
        )
    )
    db.set_source_status("indeed", "OK_WITH_RESULTS", "", 1)
    assert db.dashboard_stats(run_id=rid)["this_run"] == 1

    db.clear_job_data(
        clear_applications=True,
        clear_source_status=True,
        clear_search_runs=True,
        clear_geocode_cache=False,
    )
    stats = db.dashboard_stats()
    assert stats["total_jobs"] == 0
    assert stats["this_run"] == 0

    reloaded = svc.load()
    assert reloaded.application.first_name == "Ada"
    assert reloaded.application.email == "ada@example.com"
    print("RESET_CHECK_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
