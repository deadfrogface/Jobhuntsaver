# Codebase audit (V1)

Date: 2026-09-08. Tools: ruff, radon, vulture (from `requirements-dev.txt`), plus file-size listing.

## Tooling snapshot

### ruff (`ruff check apply core desktop`)

~221 findings dominated by **E501** (line length). Also a few E402 (intentional late imports for lazy loading), F401 unused imports, one F841. No blocking architecture issues; style cleanup is optional follow-up.

### radon (cyclomatic complexity)

Hotspots:

| Location | Complexity | Note |
|----------|------------|------|
| `ApplicationManager.prepare_and_apply` | E (~31) | Mode / submit / status branching — spaghetti-prone; central dry_run guard added |
| `ApplicationManager.can_auto_apply` | C | Safety checks — acceptable |
| `core/config.py` parsers (`_parse_*`, `load_config`) | C–F | YAML→dataclass glue |
| `core/cv_parser.py` | large file | Heuristic DE parser — keep local (see cv-parser-reuse-analysis) |
| `BaseApplier.apply` | C | Retry loop — OK |

### vulture (min confidence 80)

- One hit: redundant if in `core/cv_parser.py` (~line 499) — low priority.

## Largest Python sources (approx.)

| KB | File |
|----|------|
| 27 | `desktop/i18n.py` |
| 26 | `core/cv_parser.py` |
| 25 | `core/config.py` |
| 23 | `desktop/pages/profile.py` |
| 20 | `desktop/pages/settings.py` |
| 20 | `desktop/services/profile_merge.py` |
| 17 | `core/database.py` |
| 12 | `desktop/main_window.py` |
| 12 | `core/matcher.py` |
| 11 | `app/main.py` |

## Spaghetti / coupling notes

1. **Apply path:** per-ATS modules + `ApplicationManager` + `BaseApplier._maybe_submit` — submit safety is now centralized (dry_run / TEST MODE logs).
2. **Config duality:** `ProfileConfig` (search) vs `ApplicationProfile` (PII) documented in `core/search_preferences.py` and config docstrings; optional UI sync checkbox only.
3. **Desktop workers:** `app.main.run_pipeline` (and thus search/apply) is **lazy-imported** inside `PipelineWorker.run` so startup does not pull playwright/jobspy.
4. **Paths:** AppData (`desktop/paths.py`) vs repo `config/` — keep using AppData for user data.

## Dead Streamlit removal

| Action | Status |
|--------|--------|
| Delete `ui/app.py` | Done |
| `start.bat` → desktop | Already redirects to `python -m desktop.app` |
| README Streamlit start line | Removed |
| `requirements-dev.txt` streamlit pin | Removed |
| Docs still mentioning Streamlit historically | `docs/source-analysis.md`, `docs/ui-reuse-analysis.md`, `docs/desktop-conversion.md` (historical — leave or update later) |

Empty `ui/` package may remain with `__init__.py` only; no runtime import.

## Database indexes

See `core/database.py` SCHEMA. Added for existing query patterns:

- `idx_jobs_source_job_id` — lookup by source + source_job_id
- `idx_jobs_discovered` — dashboard day counts
- `idx_jobs_url` — `has_applied` URL checks
- `idx_apps_date` / `idx_apps_status` — application lists / counts

## Logging privacy

- `core/logging.py`: `RotatingFileHandler` (2 MB × 3).
- CV import logs **path name + char length only**, never body text at INFO.
