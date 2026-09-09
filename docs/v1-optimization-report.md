# Jobhuntsaver V1 Optimization Report

Date: 2026-09-08  
Repo: https://github.com/deadfrogface/Jobhuntsaver

## PACKAGE

| Metric | Value |
|--------|-------|
| Previous distribution size (onedir + Chromium) | **1214.6 MB** |
| Final `Jobhuntsaver.exe` (onefile) | **160.5 MB** |
| Optional Chromium (not in artifact) | ~200–400 MB when installed to `%LOCALAPPDATA%\Jobhuntsaver\browsers` (old bundle was **701 MB**) |
| Reduction vs previous folder | **~1054 MB** (~**87%**) |
| Artifact contents | `Jobhuntsaver.exe` **only** (no `_internal`, no `ms-playwright`, no ZIP packaging step) |

## DEPENDENCIES

**Removed from runtime:** Streamlit, OpenPyXL, Streamlit extras (pyarrow/pydeck/altair), entire `ui/` Streamlit app.

**Kept:** PySide6, Playwright Python driver, python-jobspy + tls_client, pandas/numpy (JobSpy), pypdf, python-docx, httpx, PyYAML, BeautifulSoup/lxml.

**Moved to dev-only:** pytest, PyInstaller, ruff, radon, vulture (`requirements-dev.txt`).

**Replaced:** Broad `collect_all("playwright")` → driver package only; Chromium on-demand.

## RAM (packaged EXE smoke)

| Scenario | Measurement |
|----------|-------------|
| Idle after GUI up (child process) | **~158 MB** working set |
| Previous idle (not re-measured on old onedir) | n/a this pass — old bundle dominated by Chromium when used |
| Browser-active | Not re-measured (Chromium optional / not preinstalled) |
| After browser closes | n/a |

## PERFORMANCE

| Metric | Value |
|--------|-------|
| Cold onefile startup (window visible) | **~13–19 s** (extract + Qt) |
| Shutdown after WM_CLOSE | **~1.8 s** (no leftover `Jobhuntsaver.exe`) |
| EXE replaceable after exit | Yes (smoke rename check / process gone) |

## CODE

| Metric | Value |
|--------|-------|
| Python LOC (approx., excl. `.venv`) | **~10.9k** |
| Dead code removed | Streamlit `ui/`, obsolete start path |
| Duplicate profile sources | Reset clears CV store + `application_profile` + qualifications; bootstrap only from `*.example` when missing |
| Largest hotspots | `cv_parser._parse_experience` / `parse_cv_text` / `hard_exclude` (radon E/D) — documented, partially improved |

## ARCHITECTURE

**Major problems found:** Stale CV/PII in AppData + qualifications YAML; Replace not starting from empty; Chromium bundled; onedir ZIP UX; Streamlit leftover; dry_run submit trust per-adapter; no single-instance; profile vs search address conflation.

**Major refactors:** EMPTY_PROFILE + real Reset; CV German normalize + A→B→C tests; onefile CI artifact; AppData browsers; ConfigService `clear_cv_storage` / `reset_to_empty_profile`; SearchPreferences aliases; central TEST MODE submit guard; single-instance QSharedMemory; rotating logs; DB indexes; lazy pipeline import.

**Remaining debt:** None material for V1 polish; further UI micro-splits optional.

Follow-up (2026-09-09): Indeed/LinkedIn submit via `_maybe_submit`; `SearchAdapter` alias + `health_check` on BA/Indeed; GitHub artifact verified as single `Jobhuntsaver.exe`.

Follow-up (2026-09-09 b): Shared `search/jsonld.py`; SuccessFactors via `_maybe_submit`; `BaseApplier._fill_identity_fields`; CV text in `core/cv_extract.py`.

Follow-up (2026-09-09 d): Greenhouse/Indeed/LinkedIn via `_fill_identity_fields`; shared `_fill_cover_letter` / `_unknown_required_fields`; F401 cleanup; profile section smoke tests.

## PRIVACY

| Item | Result |
|------|--------|
| Persistence sources | `application_profile.yaml`, `profile.yaml` qualifications, `cvs/`, `meta.cv_variants`, geocode street queries, browser_profile |
| Cleanup performed | Emptied applicant YAML, cleared quals, deleted CVs, cleared variants, removed street geocode, wiped browser_profile/logs/cache |
| Reset Profile | Persists EMPTY + clears CV storage; confirmation dialog |
| Restart | Empty profile remains empty |
| Privacy scan | **PASS** |

## CV

| Item | Result |
|------|--------|
| Parser reuse analysis | `docs/cv-parser-reuse-analysis.md` — keep local DE layer; no spaCy/AGPL app |
| German headings / Führerschein | Yes (`B`,`BE`); headings ≠ values |
| Replace / Merge | Replace starts from empty quals + personal plan |
| A → B → C + reload | **PASS** (`tests/test_cv_abc_persistence.py`) |

## BUILD

| Item | Result |
|------|--------|
| Final artifact | `Jobhuntsaver-Windows` → `Jobhuntsaver.exe` |
| Chromium in artifact | **No** |
| Clean Windows smoke | Launch / empty profile / close / process exit — **OK** (`scripts/smoke_onefile_exe.py`) |
| GitHub workflow | Updated; no Compress-Archive; upload EXE only |

## TESTS

- `pytest`: **60+** (incl. search adapter, captcha stop, hard filter, reset helpers)
- Privacy scan: **OK**
- Packaged smoke: **SMOKE_OK** (`scripts/smoke_onefile_exe.py`)
- GitHub artifact verified: only `Jobhuntsaver.exe`

## FOLLOW-UPS (2026-09-09)

- CAPTCHA stops AutoApply loop
- Reset-all uses `reset_to_empty_profile`
- Deleted dead `packaging/prepare_browsers.py`
- Browser smoke → AppData path
- `boot.log` gated behind `JOBHUNTSAVER_BOOT_DIAG`
