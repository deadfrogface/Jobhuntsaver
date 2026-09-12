# Safe Reuse / Replace / Verify — Baseline Snapshot

Date: 2026-09-10  
Baseline commit: `9a15d1c5681d1e62f46846afaf8f4ac0773dc6f5` (`main`)  
Working branch: `cursor/safe-reuse-verify-d85b`

## Test results (this environment)

| Suite | Result |
|-------|--------|
| `pytest -q -m "not network"` | **165 passed**, 2 deselected |
| `python scripts/run_cv_corpus.py` | **10/10 documents fully PASS** |
| Packaged Windows EXE open | Not runnable on Linux cloud agent — deferred to GitHub Actions `windows-smoke.yml` / `build-windows.yml` |

Reference repos cloned read-only under `/tmp/refs/` (jobradar, AutoApply, Auto-Fill-Forms, open-resume, pyresparser). Not vendored into the tree.

## What works

- Local matcher, hard filters, salary/distance/remote rules
- Canonical `ApplicationProfile` + `SearchPreferences` split (`ProfileConfig` / `ApplicantProfile` aliases)
- SQLite schema + legacy `run_id` migration
- CV corpus section-first extraction (fictional DE/EN)
- Pipeline orchestration with source timeouts / cancel (`app/main.py`)
- Submit guard (`dry_run` / review), preview dialog
- Pause via `automation_paused` + Windows Task Scheduler gate
- Shutdown manager + browser close registration
- PySide6 desktop (offscreen Qt via extracted EGL libs here; Windows CI covers EXE)

## What was broken before (historical, already fixed on baseline)

Documented in [`docs/v1-runtime-blockers.md`](v1-runtime-blockers.md) / CV docs: geocode spam, enrich hang, CV append leakage, education/work/software/skills section traps, legacy DB index crash. Baseline suite is green for these.

## Subsystem matrix

| Subsystem | Status | Notes |
|-----------|--------|-------|
| Desktop UI (PySide6) | WORKING WELL | Keep; no Electron |
| Settings | WORKING WELL | YAML + ConfigService |
| ApplicantProfile (`ApplicationProfile`) | WORKING WELL | Canonical PII profile |
| SearchPreferences | WORKING WELL | Canonical; `ProfileConfig` alias |
| Database / migrations | WORKING WELL | Inline migrations in `core/database.py` |
| CV parsing | WORKING WELL | Heuristic; fragile on novel layouts |
| Job-source adapters | MIXED | BA/Indeed OK; StepStone/XING FRAGILE (JSON-LD only) |
| Search orchestration | WORKING WELL | `app/main.py` |
| Deduplication | WORKING WELL | `core/deduplicator.py` |
| Location / geocoding | WORKING WELL | Once-per-run home + cache |
| Radius filtering | WORKING WELL | `hard_filter` + remote rules |
| Salary normalization | WORKING WELL | Annual gross EUR |
| Matching / scoring | WORKING WELL | Local 0–100; no LLM |
| ATS detection | WORKING WELL | Many fingerprints; subset have appliers |
| Application form filling | FRAGILE | DE adapters thin |
| Browser / session | WORKING WELL | Playwright persistent |
| Review-before-submit | WORKING WELL | |
| Submit guard | WORKING WELL | Central `_maybe_submit` |
| Application queue/history | WORKING WELL | |
| Scheduler | WORKING WELL | Thin Windows Task Scheduler |
| Pause / resume | WORKING WELL | Automation flag, not mid-form |
| Shutdown / cancellation | WORKING WELL | |
| Packaging | WORKING WELL | PyInstaller onefile |
| GitHub Actions | WORKING WELL | `ci.yml`, `windows-smoke.yml`, `build-windows.yml` |
| LinkedIn search module | DUPLICATED | Thin re-export of Indeed JobSpy subclass |
| Company sites | MISSING | Intentional PLACEHOLDER |
| Glassdoor / Google Jobs sources | MISSING | Rejected unless JobSpy path proven useful |
| OpenResume / pyresparser | REJECT | License / weight |
| Auto-Fill-Forms code | REJECT copy | No license |

## Planned smallest changes after baseline

1. Search: ItemList JSON-LD + HTML card / page-2 fallbacks from JobRadar patterns into StepStone/XING; LinkedIn import cleanup.
2. ATS: `partially_supported` class + harden thin DE appliers only if gap vs AutoApply is concrete.
3. CV: keep unless new failures appear.
4. Lifecycle/packaging: fix only proven bugs; prove via CI.
