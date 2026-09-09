"""SQLite persistence for Jobhuntsaver."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from core.models import ApplicationRecord, Job, JobStatus, utc_now_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    source TEXT,
    source_job_id TEXT,
    title TEXT,
    company TEXT,
    description TEXT,
    city TEXT,
    postal_code TEXT,
    address TEXT,
    latitude REAL,
    longitude REAL,
    distance_km REAL,
    remote_type TEXT,
    employment_type TEXT,
    salary_min REAL,
    salary_max REAL,
    salary_text TEXT,
    published_at TEXT,
    discovered_at TEXT,
    url TEXT,
    application_url TEXT,
    ats_type TEXT,
    match_score INTEGER DEFAULT 0,
    match_reasons TEXT DEFAULT '[]',
    rejection_reasons TEXT DEFAULT '[]',
    status TEXT DEFAULT 'new',
    duplicate_of TEXT,
    alt_sources TEXT DEFAULT '[]',
    run_id TEXT DEFAULT '',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    company TEXT,
    position TEXT,
    application_date TEXT,
    platform TEXT,
    status TEXT,
    cv_used TEXT,
    cover_letter_used TEXT,
    result TEXT,
    error_message TEXT,
    FOREIGN KEY(job_id) REFERENCES jobs(id)
);

CREATE TABLE IF NOT EXISTS geocode_cache (
    query TEXT PRIMARY KEY,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    display_name TEXT,
    cached_at TEXT
);

CREATE TABLE IF NOT EXISTS source_status (
    source TEXT PRIMARY KEY,
    status TEXT,
    message TEXT,
    checked_at TEXT,
    jobs_found INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS search_runs (
    id TEXT PRIMARY KEY,
    started_at TEXT,
    finished_at TEXT,
    status TEXT,
    stats_json TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_company_title ON jobs(company, title);
CREATE INDEX IF NOT EXISTS idx_jobs_match ON jobs(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_apps_job ON applications(job_id);
-- Query patterns: find_by_source, has_applied URL/status, dashboard date counts
CREATE INDEX IF NOT EXISTS idx_jobs_source_job_id ON jobs(source, source_job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_discovered ON jobs(discovered_at);
CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);
CREATE INDEX IF NOT EXISTS idx_apps_date ON applications(application_date);
CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connection() as conn:
            # 1) Base tables/indexes that are safe for both fresh and legacy DBs.
            #    Do NOT create idx_jobs_run_id here — legacy jobs tables lack run_id.
            conn.executescript(SCHEMA)

            # 2) Migrate older DBs that predate run_id / search_runs.
            cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
            if "run_id" not in cols:
                conn.execute("ALTER TABLE jobs ADD COLUMN run_id TEXT DEFAULT ''")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS search_runs (
                    id TEXT PRIMARY KEY,
                    started_at TEXT,
                    finished_at TEXT,
                    status TEXT,
                    stats_json TEXT DEFAULT '{}'
                )
                """
            )

            # 3) Index only after run_id is guaranteed to exist.
            cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
            if "run_id" in cols:
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_jobs_run_id ON jobs(run_id)"
                )

    def upsert_job(self, job: Job) -> None:
        data = job.to_dict()
        data["match_reasons"] = json.dumps(job.match_reasons, ensure_ascii=False)
        data["rejection_reasons"] = json.dumps(job.rejection_reasons, ensure_ascii=False)
        data["alt_sources"] = json.dumps(job.alt_sources, ensure_ascii=False)
        data["updated_at"] = utc_now_iso()
        cols = list(data.keys())
        placeholders = ", ".join("?" for _ in cols)
        col_names = ", ".join(cols)
        updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "id")
        sql = (
            f"INSERT INTO jobs ({col_names}) VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}"
        )
        with self.connection() as conn:
            conn.execute(sql, [data[c] for c in cols])

    def get_job(self, job_id: str) -> Job | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(
        self,
        *,
        min_match: int | None = None,
        max_distance: float | None = None,
        statuses: list[str] | None = None,
        hide_applied: bool = False,
        hide_duplicates: bool = True,
        remote_types: list[str] | None = None,
        source: str | None = None,
        company_query: str | None = None,
        title_query: str | None = None,
        city_query: str | None = None,
        limit: int = 500,
    ) -> list[Job]:
        clauses: list[str] = []
        params: list[Any] = []
        if min_match is not None:
            clauses.append("match_score >= ?")
            params.append(min_match)
        if max_distance is not None:
            clauses.append("(distance_km IS NULL OR distance_km <= ? OR remote_type = 'remote')")
            params.append(max_distance)
        if statuses:
            clauses.append(f"status IN ({','.join('?' for _ in statuses)})")
            params.extend(statuses)
        if hide_applied:
            clauses.append("status != ?")
            params.append(JobStatus.APPLIED.value)
        if hide_duplicates:
            clauses.append("duplicate_of IS NULL")
        if remote_types:
            clauses.append(f"remote_type IN ({','.join('?' for _ in remote_types)})")
            params.extend(remote_types)
        if source:
            clauses.append("source = ?")
            params.append(source)
        if company_query:
            clauses.append("LOWER(company) LIKE ?")
            params.append(f"%{company_query.lower()}%")
        if title_query:
            clauses.append("LOWER(title) LIKE ?")
            params.append(f"%{title_query.lower()}%")
        if city_query:
            clauses.append("LOWER(city) LIKE ?")
            params.append(f"%{city_query.lower()}%")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = (
            f"SELECT * FROM jobs{where} "
            "ORDER BY match_score DESC, discovered_at DESC LIMIT ?"
        )
        params.append(limit)
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_job(r) for r in rows]

    def update_job_status(self, job_id: str, status: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
                (status, utc_now_iso(), job_id),
            )

    def has_applied(self, job: Job) -> bool:
        """Hard safety: never apply twice (job id, url, or likely duplicate)."""
        with self.connection() as conn:
            # Direct status
            row = conn.execute(
                "SELECT id FROM jobs WHERE id = ? AND status = ?",
                (job.id, JobStatus.APPLIED.value),
            ).fetchone()
            if row:
                return True
            # Application table
            row = conn.execute(
                "SELECT id FROM applications WHERE job_id = ? AND status = ?",
                (job.id, JobStatus.APPLIED.value),
            ).fetchone()
            if row:
                return True
            # URL match already applied
            if job.url or job.application_url:
                row = conn.execute(
                    """
                    SELECT id FROM jobs
                    WHERE status = ?
                      AND (
                        (url != '' AND url = ?)
                        OR (application_url != '' AND application_url = ?)
                        OR (application_url != '' AND application_url = ?)
                        OR (url != '' AND url = ?)
                      )
                    LIMIT 1
                    """,
                    (
                        JobStatus.APPLIED.value,
                        job.url,
                        job.application_url,
                        job.url,
                        job.application_url,
                    ),
                ).fetchone()
                if row:
                    return True
            # Likely duplicate by company+title
            row = conn.execute(
                """
                SELECT id FROM jobs
                WHERE status = ?
                  AND LOWER(company) = LOWER(?)
                  AND LOWER(title) = LOWER(?)
                LIMIT 1
                """,
                (JobStatus.APPLIED.value, job.company, job.title),
            ).fetchone()
            return bool(row)

    def count_applications_today(self) -> int:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM applications WHERE application_date LIKE ?",
                (f"{day}%",),
            ).fetchone()
        return int(row["c"] if row else 0)

    def list_applications(
        self,
        *,
        statuses: list[str] | None = None,
        limit: int = 500,
    ) -> list[ApplicationRecord]:
        sql = "SELECT * FROM applications"
        params: list[Any] = []
        if statuses:
            placeholders = ", ".join("?" for _ in statuses)
            sql += f" WHERE status IN ({placeholders})"
            params.extend(statuses)
        sql += " ORDER BY application_date DESC LIMIT ?"
        params.append(limit)
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        result: list[ApplicationRecord] = []
        for row in rows:
            data = dict(row)
            result.append(
                ApplicationRecord(
                    id=data.get("id") or "",
                    job_id=data.get("job_id") or "",
                    company=data.get("company") or "",
                    position=data.get("position") or "",
                    application_date=data.get("application_date") or "",
                    platform=data.get("platform") or "",
                    status=data.get("status") or "",
                    cv_used=data.get("cv_used") or "",
                    cover_letter_used=data.get("cover_letter_used") or "",
                    result=data.get("result") or "",
                    error_message=data.get("error_message") or "",
                )
            )
        return result

    def get_meta(self, key: str) -> str | None:
        with self.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
                """
            )
            row = conn.execute(
                "SELECT value FROM app_meta WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO app_meta (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (key, value, utc_now_iso()),
            )

    def save_application(self, record: ApplicationRecord) -> str:
        if not record.id:
            record.id = str(uuid.uuid4())
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO applications (
                    id, job_id, company, position, application_date, platform,
                    status, cv_used, cover_letter_used, result, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.job_id,
                    record.company,
                    record.position,
                    record.application_date,
                    record.platform,
                    record.status,
                    record.cv_used,
                    record.cover_letter_used,
                    record.result,
                    record.error_message,
                ),
            )
        return record.id

    def get_geocode(self, query: str) -> tuple[float, float, str] | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT latitude, longitude, display_name FROM geocode_cache WHERE query = ?",
                (query.lower().strip(),),
            ).fetchone()
        if not row:
            return None
        return float(row["latitude"]), float(row["longitude"]), row["display_name"] or ""

    def set_geocode(
        self, query: str, latitude: float, longitude: float, display_name: str = ""
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO geocode_cache (query, latitude, longitude, display_name, cached_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(query) DO UPDATE SET
                    latitude=excluded.latitude,
                    longitude=excluded.longitude,
                    display_name=excluded.display_name,
                    cached_at=excluded.cached_at
                """,
                (query.lower().strip(), latitude, longitude, display_name, utc_now_iso()),
            )

    def set_source_status(
        self, source: str, status: str, message: str = "", jobs_found: int = 0
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO source_status (source, status, message, checked_at, jobs_found)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source) DO UPDATE SET
                    status=excluded.status,
                    message=excluded.message,
                    checked_at=excluded.checked_at,
                    jobs_found=excluded.jobs_found
                """,
                (source, status, message, utc_now_iso(), jobs_found),
            )

    def list_source_status(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM source_status ORDER BY source"
            ).fetchall()
        return [dict(r) for r in rows]

    def dashboard_stats(self, run_id: str | None = None) -> dict[str, int]:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.connection() as conn:
            found = conn.execute(
                "SELECT COUNT(*) AS c FROM jobs WHERE discovered_at LIKE ?",
                (f"{day}%",),
            ).fetchone()["c"]
            new = conn.execute(
                "SELECT COUNT(*) AS c FROM jobs WHERE status = 'new' AND discovered_at LIKE ?",
                (f"{day}%",),
            ).fetchone()["c"]
            matches = conn.execute(
                "SELECT COUNT(*) AS c FROM jobs WHERE match_score >= 75 AND duplicate_of IS NULL"
            ).fetchone()["c"]
            applied = conn.execute(
                "SELECT COUNT(*) AS c FROM applications WHERE status = 'applied' AND application_date LIKE ?",
                (f"{day}%",),
            ).fetchone()["c"]
            needs = conn.execute(
                "SELECT COUNT(*) AS c FROM jobs WHERE status = 'needs_review'"
            ).fetchone()["c"]
            errors = conn.execute(
                "SELECT COUNT(*) AS c FROM jobs WHERE status = 'failed'"
            ).fetchone()["c"]
            captcha = conn.execute(
                "SELECT COUNT(*) AS c FROM jobs WHERE status = 'captcha'"
            ).fetchone()["c"]
            this_run = 0
            rid = run_id or self.latest_run_id()
            if rid:
                this_run = conn.execute(
                    "SELECT COUNT(*) AS c FROM jobs WHERE run_id = ? AND duplicate_of IS NULL",
                    (rid,),
                ).fetchone()["c"]
            total_jobs = conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"]
        return {
            "jobs_found_today": int(found),
            "new_today": int(new),
            "matches_ge_75": int(matches),
            "applications_today": int(applied),
            "needs_review": int(needs),
            "errors": int(errors),
            "captcha": int(captcha),
            "this_run": int(this_run),
            "total_jobs": int(total_jobs),
        }

    def start_search_run(self, run_id: str | None = None) -> str:
        rid = run_id or uuid.uuid4().hex
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO search_runs (id, started_at, finished_at, status, stats_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (rid, utc_now_iso(), "", "running", "{}"),
            )
        return rid

    def finish_search_run(self, run_id: str, status: str, stats: dict[str, Any] | None = None) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE search_runs SET finished_at = ?, status = ?, stats_json = ? WHERE id = ?",
                (utc_now_iso(), status, json.dumps(stats or {}, ensure_ascii=False), run_id),
            )

    def latest_run_id(self) -> str | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id FROM search_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        return str(row["id"]) if row else None

    def clear_job_data(
        self,
        *,
        clear_applications: bool = True,
        clear_source_status: bool = True,
        clear_search_runs: bool = True,
        clear_geocode_cache: bool = False,
    ) -> dict[str, int]:
        """Remove job search data; never touches applicant profile files."""
        counts: dict[str, int] = {}
        with self.connection() as conn:
            if clear_applications:
                counts["applications"] = conn.execute("SELECT COUNT(*) AS c FROM applications").fetchone()["c"]
                conn.execute("DELETE FROM applications")
            counts["jobs"] = conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"]
            conn.execute("DELETE FROM jobs")
            if clear_source_status:
                counts["source_status"] = conn.execute(
                    "SELECT COUNT(*) AS c FROM source_status"
                ).fetchone()["c"]
                conn.execute("DELETE FROM source_status")
            if clear_search_runs:
                counts["search_runs"] = conn.execute(
                    "SELECT COUNT(*) AS c FROM search_runs"
                ).fetchone()["c"]
                conn.execute("DELETE FROM search_runs")
            if clear_geocode_cache:
                counts["geocode_cache"] = conn.execute(
                    "SELECT COUNT(*) AS c FROM geocode_cache"
                ).fetchone()["c"]
                conn.execute("DELETE FROM geocode_cache")
        return {k: int(v) for k, v in counts.items()}

    def find_existing_by_source(self, source: str, source_job_id: str) -> Job | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE source = ? AND source_job_id = ?",
                (source, source_job_id),
            ).fetchone()
        return self._row_to_job(row) if row else None

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        data = dict(row)
        data.pop("updated_at", None)
        return Job.from_dict(data)
