"""Main search / apply pipeline."""

from __future__ import annotations

import argparse
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path

from apply.detector import ATSDetector, ats_coverage_bucket
from apply.manager import ApplicationManager
from browser.browser_manager import BrowserManager
from core.cancel import cancel_active_searches, register_executor, unregister_executor
from core.config import AppConfig, load_config
from core.database import Database
from core.deduplicator import deduplicate
from core.location import LocationService, enrich_job_locations
from core.logging import RunLogger
from core.matcher import score_job
from core.models import JobStatus, OperatingMode
from core.source_health import SourceHealthStatus
from search.base import SearchQuery
from search.registry import build_sources

# Hard ceiling per job board so one hung source cannot freeze the whole run.
SOURCE_SEARCH_TIMEOUT_S = 120

# Executor cancel registry lives in core.cancel (shared with BA detail pools).


def _search_location(home_address: str) -> str:
    """Prefer city name for BA/Indeed queries (e.g. Musterstadt from full address)."""
    parts = [p.strip() for p in home_address.split(",") if p.strip()]
    for part in reversed(parts):
        low = part.lower()
        if low in {"germany", "deutschland", "de"}:
            continue
        tokens = part.split()
        words = [t for t in tokens if not any(c.isdigit() for c in t)]
        if not words:
            continue
        # "12345 Musterstadt" → Musterstadt
        if tokens and tokens[0].isdigit():
            return " ".join(words)
        # Skip street lines like "Musterstraße 1"
        if any(c.isdigit() for c in part):
            continue
        return " ".join(words)
    return ""


def build_queries(config: AppConfig) -> list[SearchQuery]:
    loc = config.profile.location
    titles = config.profile.jobs.desired_titles + config.profile.jobs.alternative_titles
    if not titles:
        return []
    place = _search_location(loc.home_address)
    queries: list[SearchQuery] = []
    if place:
        for title in titles:
            queries.append(
                SearchQuery(
                    keyword=title,
                    location=place,
                    radius_km=loc.max_distance_km,
                    max_results=40,
                    published_within_days=config.settings.published_within_days,
                )
            )
    if loc.allow_remote_germany:
        for title in titles[:3]:
            queries.append(
                SearchQuery(
                    keyword=title,
                    location="Remote",
                    radius_km=loc.max_distance_km,
                    max_results=20,
                    published_within_days=config.settings.published_within_days,
                )
            )
    return queries



def enrich_locations(jobs, location: LocationService, progress_callback=None, should_stop=None):
    """Backward-compatible wrapper around ``enrich_job_locations``."""
    return enrich_job_locations(
        jobs,
        location,
        progress_callback=progress_callback,
        should_stop=should_stop,
    )


def _search_source_with_timeout(
    source,
    queries,
    timeout_s: float = SOURCE_SEARCH_TIMEOUT_S,
    should_stop=None,
):
    pool = ThreadPoolExecutor(max_workers=1)
    register_executor(pool)
    fut = pool.submit(source.safe_search, queries)
    try:
        deadline = __import__("time").monotonic() + timeout_s
        while True:
            if should_stop and should_stop():
                try:
                    pool.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    pool.shutdown(wait=False)
                return [], "cancelled", None
            remaining = deadline - __import__("time").monotonic()
            if remaining <= 0:
                try:
                    pool.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    pool.shutdown(wait=False)
                return [], f"Timeout after {int(timeout_s)}s", None
            try:
                return fut.result(timeout=min(0.5, remaining))
            except FuturesTimeout:
                continue
    finally:
        unregister_executor(pool)
        try:
            pool.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            try:
                pool.shutdown(wait=False)
            except Exception:
                pass
        except Exception:
            pass


def run_pipeline(
    config: AppConfig | None = None,
    mode: str | None = None,
    progress_callback=None,
    should_stop=None,
) -> dict:
    def progress(message: str) -> None:
        if progress_callback:
            try:
                progress_callback(message)
            except Exception:
                pass

    def stopped() -> bool:
        try:
            return bool(should_stop and should_stop())
        except Exception:
            return False

    config = config or load_config()
    if mode:
        config.settings.mode = mode

    if getattr(config.settings, "automation_paused", False):
        progress("Automatisierung pausiert — Pipeline nicht gestartet.")
        return {
            "total": 0,
            "cancelled": True,
            "paused": True,
            "source_errors": [],
            "source_results": {},
            "matches": 0,
            "new": 0,
            "applied": 0,
        }

    run = RunLogger(config.root / config.settings.logs_dir)
    run_id = uuid.uuid4().hex
    run.info(f"Run started id={run_id}")
    progress("Suche gestartet…")
    db = Database(config.db_path)
    db.start_search_run(run_id)
    location = LocationService(db, config)
    home = location.resolve_home()
    if home.warning:
        progress(home.warning)
        run.info(home.warning)

    cancelled = False
    queries = build_queries(config)
    sources = build_sources(config.settings.enabled_sources)
    all_jobs = []
    source_errors: list[str] = []
    source_results: dict[str, dict] = {}
    for source in sources:
        if stopped():
            cancelled = True
            run.info("Pipeline cancelled during search")
            progress("Abgebrochen.")
            break
        progress(f"Suche {source.source_id}…")
        placeholder = source.source_id == "company_sites"
        jobs, err, detail = _search_source_with_timeout(
            source, queries, should_stop=stopped
        )
        if err:
            run.error(f"{source.source_id}: {err}")
            source_errors.append(f"{source.source_id}: {err}")
            status = SourceHealthStatus.from_outcome(
                jobs_found=0,
                error=err,
                detail_stage=getattr(detail, "stage", None) if detail else None,
                source_id=source.source_id,
                placeholder=placeholder,
            )
            msg = detail.short_message() if detail else err
            if detail:
                run.error(detail.detail())
            db.set_source_status(source.source_id, status.value, msg, 0)
            source_results[source.source_id] = {
                "status": status.value,
                "jobs": 0,
                "error": msg,
            }
            progress(
                f"{source.source_id}: {status.value} — andere Quellen laufen weiter."
            )
            continue
        status = SourceHealthStatus.from_outcome(
            jobs_found=len(jobs),
            source_id=source.source_id,
            placeholder=placeholder,
        )
        run.info(f"{source.source_id}: {len(jobs)} jobs [{status.value}]")
        note = ""
        if status == SourceHealthStatus.OK_EMPTY:
            note = "0 Treffer (Quelle antwortete, aber leer — nicht als kaputt werten, prüfen)"
        elif status == SourceHealthStatus.PLACEHOLDER:
            note = "Placeholder — absichtlich keine Jobs in v1"
        db.set_source_status(source.source_id, status.value, note, len(jobs))
        source_results[source.source_id] = {
            "status": status.value,
            "jobs": len(jobs),
            "error": note,
        }
        for job in jobs:
            job.run_id = run_id
        all_jobs.extend(jobs)

    total = len(all_jobs)
    run.info(f"{total} total results")

    if not cancelled and not stopped():
        progress("Standorte anreichern: 0/? …")
        all_jobs = enrich_job_locations(
            all_jobs,
            location,
            progress_callback=progress_callback,
            should_stop=should_stop,
        )
        if stopped():
            cancelled = True
    else:
        cancelled = cancelled or stopped()

    progress("Duplikate entfernen…")
    all_jobs = deduplicate(all_jobs)
    primary = [j for j in all_jobs if not j.duplicate_of]
    duplicates_removed = len(all_jobs) - len(primary)
    run.info(f"{duplicates_removed} duplicates marked")

    progress("Jobs matchen…")
    scored = []
    outside = 0
    new_count = 0
    known = 0
    ats_counts = {"supported": 0, "detected_unsupported": 0, "unknown": 0}
    for job in primary:
        if stopped():
            cancelled = True
            break
        existing = (
            db.find_existing_by_source(job.source, job.source_job_id)
            if job.source_job_id
            else None
        )
        if existing and existing.status == JobStatus.APPLIED.value:
            known += 1
            continue
        already = db.has_applied(job)
        job.ats_type = ATSDetector.detect(job.application_url or job.url)
        bucket = ats_coverage_bucket(job.ats_type)
        ats_counts[bucket] = ats_counts.get(bucket, 0) + 1
        job.run_id = run_id
        result = score_job(job, config, already_applied=already)
        job.match_score = result.score
        job.match_reasons = result.match_reasons
        job.rejection_reasons = result.rejection_reasons
        if result.excluded:
            if result.exclude_reason and "km" in (result.exclude_reason or ""):
                outside += 1
            job.status = JobStatus.IGNORED.value
        else:
            job.status = existing.status if existing else JobStatus.NEW.value
            if not existing:
                new_count += 1
        db.upsert_job(job)
        scored.append(job)

    for job in all_jobs:
        if job.duplicate_of:
            job.run_id = run_id
            db.upsert_job(job)

    run.info(f"{outside} outside {config.profile.location.max_distance_km} km removed/ignored")
    run.info(f"{known} already known/applied skipped")
    run.info(f"{new_count} new jobs")
    matches = [
        j
        for j in scored
        if j.match_score >= config.settings.minimum_match_for_auto_apply
        and j.status != JobStatus.IGNORED.value
    ]
    run.info(f"{len(matches)} matches ≥{config.settings.minimum_match_for_auto_apply}%")

    stats = {
        "total": total,
        "raw_results": total,
        "duplicates": duplicates_removed,
        "distance_removed": outside,
        "outside": outside,
        "new": new_count,
        "new_jobs": new_count,
        "matches": len(matches),
        "applied": 0,
        "needs_review": 0,
        "captcha": 0,
        "failed": 0,
        "run_id": run_id,
        "cancelled": cancelled,
        "source_errors": source_errors,
        "source_results": source_results,
        "geocode_resolved": location.stats.resolved,
        "geocode_cached": location.stats.cached,
        "geocode_failed": location.stats.failed,
        "geocode_failures": location.stats.failed,
        "home_updated": location.home_updated,
        "home_resolved": location.home_resolved,
        "home_warning": location.home_warning,
        "ats_supported": ats_counts.get("supported", 0),
        "ats_detected_unsupported": ats_counts.get("detected_unsupported", 0),
        "ats_unknown": ats_counts.get("unknown", 0),
        "ats_attempted": 0,
        "ats_review_required": 0,
        "ats_completed": 0,
    }

    if cancelled:
        db.finish_search_run(run_id, "cancelled", stats)
        progress("Abgebrochen.")
        run.info("Finished (cancelled)")
        return stats

    if config.settings.mode == OperatingMode.SEARCH_ONLY.value:
        run.info("Mode search_only — no applications")
        run.info("Finished")
        db.finish_search_run(run_id, "ok", stats)
        progress("Suche abgeschlossen.")
        return stats

    browser = None
    try:
        progress("Browser starten…")
        browser = BrowserManager(
            config.root / config.settings.browser_profile_dir,
            headless=config.settings.headless,
        )
        page = browser.get_page()
        manager = ApplicationManager(config, db, page=page)
        for job in matches:
            if stopped():
                run.info("Pipeline cancelled during applications")
                progress("Abgebrochen.")
                cancelled = True
                break
            if manager.failed_this_run >= config.settings.max_failed_applications_per_run:
                run.info("Failure limit reached — stopping AutoApply (search already done)")
                break
            if manager.applied_this_run >= config.settings.max_applications_per_run:
                run.info("Application limit reached")
                break
            ats = job.ats_type or "ATS"
            progress(f"Öffne {ats}: {job.company} – {job.title[:40]}")
            stats["ats_attempted"] = int(stats.get("ats_attempted") or 0) + 1
            result = manager.prepare_and_apply(job)
            label = job.title[:40]
            if result.captcha_detected:
                stats["captcha"] += 1
                run.info(f"{label} → CAPTCHA → stopping AutoApply (never bypass)")
                progress("CAPTCHA erkannt — Bewerbungslauf gestoppt.")
                break
            elif result.submitted:
                stats["applied"] += 1
                stats["ats_completed"] = int(stats.get("ats_completed") or 0) + 1
                run.info(f"{label} → application successful")
            elif result.needs_review or result.dry_run_stopped or result.manual_required:
                stats["needs_review"] += 1
                stats["ats_review_required"] = int(stats.get("ats_review_required") or 0) + 1
                if result.dry_run_stopped:
                    progress("Dry Run: vor dem Absenden gestoppt — Vorschau in Bewerbungen.")
                run.info(f"{label} → needs_review ({result.error_message})")
            else:
                stats["failed"] += 1
                run.info(f"{label} → failed ({result.error_message})")
    except Exception as exc:
        run.error(f"Browser/apply pipeline error: {exc}")
        progress("Bewerbungslauf fehlgeschlagen. Details stehen in den Logs.")
    finally:
        if browser:
            browser.close()

    stats["cancelled"] = cancelled
    db.finish_search_run(run_id, "cancelled" if cancelled else "ok", stats)
    run.info(
        f"Finished: {stats['applied']} applications successful, "
        f"{stats['needs_review']} Needs Review, {stats['captcha']} CAPTCHA, {stats['failed']} Failed"
    )
    progress("Lauf abgeschlossen." if not cancelled else "Abgebrochen.")
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Jobhuntsaver")
    parser.add_argument(
        "--mode",
        choices=[m.value for m in OperatingMode],
        default=None,
        help="Override operating mode",
    )
    parser.add_argument("--config-dir", type=Path, default=None)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single headless pipeline pass and exit (scheduler entrypoint).",
    )
    args = parser.parse_args(argv)
    # Prefer AppData config when scheduled/packaged so GUI and task share profile.
    try:
        from desktop.services import ConfigService

        config = ConfigService().load()
    except Exception:
        config = load_config()
    run_pipeline(config, mode=args.mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
