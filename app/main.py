"""Main search / apply pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from apply.detector import ATSDetector
from apply.manager import ApplicationManager
from browser.browser_manager import BrowserManager
from core.config import AppConfig, load_config
from core.database import Database
from core.deduplicator import deduplicate
from core.location import LocationService
from core.logging import RunLogger
from core.matcher import score_job
from core.models import JobStatus, OperatingMode
from search.base import SearchQuery
from search.registry import build_sources


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
    return "Musterstadt"


def build_queries(config: AppConfig) -> list[SearchQuery]:
    loc = config.profile.location
    titles = config.profile.jobs.desired_titles + config.profile.jobs.alternative_titles
    if not titles:
        titles = ["Sachbearbeiter"]
    place = _search_location(loc.home_address)
    queries = []
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


def enrich_locations(jobs, location: LocationService):
    for job in jobs:
        if job.remote_type == "remote":
            job.distance_km = None
            continue
        lat, lon, dist = location.distance_for_job_location(
            address=job.address,
            city=job.city,
            postal_code=job.postal_code,
            latitude=job.latitude,
            longitude=job.longitude,
        )
        if lat is not None:
            job.latitude = lat
            job.longitude = lon
        if dist is not None:
            job.distance_km = dist
    return jobs


def run_pipeline(
    config: AppConfig | None = None,
    mode: str | None = None,
    progress_callback=None,
) -> dict:
    def progress(message: str) -> None:
        if progress_callback:
            try:
                progress_callback(message)
            except Exception:
                pass

    config = config or load_config()
    if mode:
        config.settings.mode = mode

    run = RunLogger(config.root / config.settings.logs_dir)
    run.info("Run started")
    progress("Suche gestartet…")
    db = Database(config.db_path)
    location = LocationService(db, config)
    location.ensure_home_coords()

    queries = build_queries(config)
    sources = build_sources(config.settings.enabled_sources)
    all_jobs = []
    for source in sources:
        progress(f"Suche {source.source_id}…")
        jobs, err = source.safe_search(queries)
        if err:
            run.error(f"{source.source_id}: {err}")
            db.set_source_status(source.source_id, "error", err, 0)
            progress(f"{source.source_id}-Suche fehlgeschlagen. Andere Quellen laufen weiter.")
            continue
        run.info(f"{source.source_id}: {len(jobs)} jobs")
        db.set_source_status(source.source_id, "ok", "", len(jobs))
        all_jobs.extend(jobs)

    total = len(all_jobs)
    run.info(f"{total} total results")

    progress("Standorte anreichern…")
    all_jobs = enrich_locations(all_jobs, location)
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
    for job in primary:
        existing = db.find_existing_by_source(job.source, job.source_job_id) if job.source_job_id else None
        if existing and existing.status == JobStatus.APPLIED.value:
            known += 1
            continue
        already = db.has_applied(job)
        job.ats_type = ATSDetector.detect(job.application_url or job.url)
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
        # also store duplicate markers
        scored.append(job)

    for job in all_jobs:
        if job.duplicate_of:
            db.upsert_job(job)

    run.info(f"{outside} outside {config.profile.location.max_distance_km} km removed/ignored")
    run.info(f"{known} already known/applied skipped")
    run.info(f"{new_count} new jobs")
    matches = [j for j in scored if j.match_score >= config.settings.minimum_match_for_auto_apply and j.status != JobStatus.IGNORED.value]
    run.info(f"{len(matches)} matches ≥{config.settings.minimum_match_for_auto_apply}%")

    stats = {
        "total": total,
        "duplicates": duplicates_removed,
        "outside": outside,
        "new": new_count,
        "matches": len(matches),
        "applied": 0,
        "needs_review": 0,
        "captcha": 0,
        "failed": 0,
    }

    if config.settings.mode == OperatingMode.SEARCH_ONLY.value:
        run.info("Mode search_only — no applications")
        run.info("Finished")
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
            if manager.failed_this_run >= config.settings.max_failed_applications_per_run:
                run.info("Failure limit reached — stopping AutoApply (search already done)")
                break
            if manager.applied_this_run >= config.settings.max_applications_per_run:
                run.info("Application limit reached")
                break
            ats = job.ats_type or "ATS"
            progress(f"Öffne {ats}: {job.company} – {job.title[:40]}")
            result = manager.prepare_and_apply(job)
            label = job.title[:40]
            if result.captcha_detected:
                stats["captcha"] += 1
                run.info(f"{label} → CAPTCHA → skipped")
            elif result.submitted:
                stats["applied"] += 1
                run.info(f"{label} → application successful")
            elif result.needs_review or result.dry_run_stopped or result.manual_required:
                stats["needs_review"] += 1
                if result.dry_run_stopped:
                    progress("Dry Run: vor dem Absenden gestoppt.")
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

    run.info(
        f"Finished: {stats['applied']} applications successful, "
        f"{stats['needs_review']} Needs Review, {stats['captcha']} CAPTCHA, {stats['failed']} Failed"
    )
    progress("Lauf abgeschlossen.")
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
    args = parser.parse_args(argv)
    config = load_config()
    run_pipeline(config, mode=args.mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
