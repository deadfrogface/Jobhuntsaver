# V1 runtime blockers — acceptance notes (EXE log evidence)

## A. Home geocoding

- Resolved **once** per `LocationService` / run via `resolve_home()`.
- Successful coords persisted on profile (`home_latitude` / `home_longitude`).
- Failures: **no** silent Germany-center fallback for distance filtering.
- UI: Dashboard warning + run-finished dialog show `home_warning`.
- Tests: `tests/test_location.py` (once-per-run, no distance distortion).

## B. Location enrichment

- Deduped unique queries, N/M progress, cancel-aware, 5s timeout, negative cache + TTL.
- Remote jobs skipped; attempt cap per run.
- Tests cover dedupe / cancel / remote skip.

## C. Shutdown during search

- Cancel workers → `cancel_active_searches()` (ThreadPoolExecutor shut down).
- Thread wait **15s**; RuntimeError on deleted QThread swallowed.
- Unregister before `deleteLater` to avoid libshiboken double-free.
- Packaged close still uses `ApplicationShutdownManager`.

## D. Pre-submit preview + dry-run

- Dry-run submit guard unchanged (`TEST MODE: … will not allow final submit`).
- `apply/preview.py` + Applications **Bewerbungsvorschau** dialog.
- Unsupported ATS stores preview text on the application record.

## E. ATS coverage

- Expanded fingerprints; `classify_ats_support` / coverage buckets in run stats.
- Unknown → needs_review + manual URL + explanation (not pretended success).

## F. Source health

- Enum: `OK_WITH_RESULTS`, `OK_EMPTY`, `TIMEOUT`, `BLOCKED`, `PARSER_ERROR`,
  `NETWORK_ERROR`, `AUTH_REQUIRED`, `RATE_LIMITED`, `DISABLED`, `PLACEHOLDER`, …
- `company_sites` = PLACEHOLDER (intentional empty).
- StepStone/XING empty ≠ healthy-with-results (`OK_EMPTY`).

## G. Run accounting

- `search_runs.stats_json` includes raw/dup/distance/new/matches, source_results,
  geocode_*, home_*, ats_* metrics.
- Dashboard **Dieser Lauf** + run detail line.
