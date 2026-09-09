"""Smoke: search pipeline location enrichment cannot hang.

Uses a temporary LOCALAPPDATA tree and empty DB. Geocode is stubbed so the
test is deterministic offline; the hang regression (home re-geocode per job)
is still exercised via LocationService.ensure_home_coords call patterns.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from core.config import AppConfig, LocationConfig, SearchPreferences, SettingsConfig
    from core.database import Database
    from core.location import LocationService, enrich_job_locations
    from core.models import Job, RemoteType

    with tempfile.TemporaryDirectory(prefix="jhs-smoke-") as tmp:
        os.environ["LOCALAPPDATA"] = tmp
        db_path = Path(tmp) / "Jobhuntsaver" / "data" / "jobs.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db = Database(db_path)
        stats0 = db.dashboard_stats()
        assert stats0["total_jobs"] == 0, stats0

        cfg = AppConfig(
            profile=SearchPreferences(
                location=LocationConfig(
                    home_address="Hafenweg 87, 28195 Bremen",
                    max_distance_km=20,
                    # Intentionally no lat/lon — must resolve once, not per job
                )
            ),
            settings=SettingsConfig(mode="search_only", dry_run=True),
            root=Path(tmp) / "Jobhuntsaver",
        )
        svc = LocationService(db, cfg, timeout_s=2.0)

        # Stub Nominatim: empty for street, success for city fallback once
        calls = {"n": 0}

        class _Client:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get(self, *a, **k):
                calls["n"] += 1
                q = (k.get("params") or {}).get("q") or ""
                class _Resp:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        if "Hafenweg" in str(q):
                            return []
                        return [{"lat": "53.07", "lon": "8.80", "display_name": "Bremen"}]

                return _Resp()

        import httpx

        httpx.Client = _Client  # type: ignore[misc,assignment]

        jobs = []
        for i in range(80):
            jobs.append(
                Job(
                    id=f"j{i}",
                    source="smoke",
                    source_job_id=str(i),
                    title=f"Job {i}",
                    company="Firma",
                    city="Bremen" if i % 2 == 0 else "Hamburg",
                    remote_type=RemoteType.REMOTE.value if i % 5 == 0 else RemoteType.ONSITE.value,
                )
            )

        progress: list[str] = []
        t0 = time.time()
        enrich_job_locations(jobs, svc, progress_callback=progress.append)
        elapsed = time.time() - t0

        # Without the fix this would be ~80+ Nominatim calls (~90s+). With fix: few calls.
        assert calls["n"] < 15, f"too many geocode calls: {calls['n']}"
        assert elapsed < 30, f"enrich too slow: {elapsed:.1f}s"
        assert any("Standorte anreichern:" in p for p in progress), progress[:5]
        assert any("gelöst" in p or "Cache" in p for p in progress)

        # Persist a run and prove clean→populated→clear
        rid = db.start_search_run()
        for j in jobs[:5]:
            j.run_id = rid
            db.upsert_job(j)
        assert db.dashboard_stats(run_id=rid)["this_run"] == 5
        db.clear_job_data()
        assert db.dashboard_stats()["total_jobs"] == 0

        print(
            f"OK enrich {elapsed:.2f}s calls={calls['n']} "
            f"unique={svc.stats.unique_queries} remote={svc.stats.remote_skipped}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
