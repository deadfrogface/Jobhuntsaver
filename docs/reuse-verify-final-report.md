# Safe Reuse / Replace / Verify — Final Report

Date: 2026-09-10  
Branch: `cursor/safe-reuse-verify-d85b`  
Final commit SHA: `287d5d27293cae065321944c192a96398b2142ac`

## 1. FINAL COMMIT SHA

`287d5d27293cae065321944c192a96398b2142ac`

Commits on branch:

1. `702b26f` — baseline matrix + green test snapshot  
2. `bc5fe06` — StepStone/XING JobRadar fallback adaptation + LinkedIn cleanup  
3. `287d5d2` — DE ATS partially_supported + German profile field helper  

## 2. BASELINE SUMMARY

**Worked before (and still works):**

- PySide6 desktop, settings, ApplicationProfile / SearchPreferences split  
- SQLite + legacy `run_id` migration  
- BA / Indeed search, local matcher, salary/distance/remote rules  
- Location geocode once-per-run + cache  
- Dedup, submit guard, preview, pause flag, shutdown manager  
- Packaging (PyInstaller onefile) + CI  

**Broken / fragile before (historical or remaining):**

- StepStone/XING JSON-LD-only → empty results when structured data missing (**improved**)  
- Thin DE ATS oversold as fully `supported` (**reclassified + hardened**)  
- CV education/work/software leakage — already fixed on baseline; corpus 10/10  
- Company sites placeholder — intentional MISSING  

Baseline tests: **165 passed** (`not network`); CV corpus **10/10**.

## 3. SUBSYSTEM DECISIONS

| Subsystem | Decision | Reason |
|-----------|----------|--------|
| Desktop UI (PySide6) | KEEP | Stable; Electron would cost more |
| Settings | KEEP | Working |
| ApplicationProfile | KEEP | Canonical PII profile |
| SearchPreferences | KEEP | Canonical search prefs |
| Database / migrations | KEEP | Legacy path fixed |
| Search orchestration | KEEP | Timeouts/cancel already solid |
| Dedup / location / radius / salary / matcher | KEEP | Jobhuntsaver-specific, tested |
| Bundesagentur adapter | KEEP | Already ahead of JobRadar (API v6) |
| Indeed / JobSpy | KEEP | Working |
| StepStone / XING | ADAPT | JobRadar ItemList + HTML + page-2 fallbacks |
| LinkedIn search module | ADAPT | Single canonical module; removed indeed duplicate |
| Glassdoor / Google Jobs | REJECT | Fragility without proven gain |
| Browser manager | KEEP | AutoApply-adapted, packaging OK |
| Submit guard / preview / pause / shutdown | KEEP | Central guards, tests green |
| Greenhouse/Lever/Ashby/Indeed/LinkedIn/Workday appliers | KEEP | Already adapted from AutoApply |
| Personio/SmartRecruiters/SuccessFactors/StepStone apply | ADAPT | `partially_supported` + DE field helpers |
| Taleo/iCIMS/Teamtailor/etc. | KEEP detect + needs_review | No untested full appliers |
| CV parser | KEEP | Corpus 10/10; OpenResume/pyresparser rejected |
| Packaging / CI | KEEP | Proven paths |
| JobRadar wholesale / LLM scoring | REJECT | Offline/no-LLM policy |
| Auto-Fill-Forms code | REJECT copy | No license |
| OpenResume | REJECT | AGPL + wrong stack |
| pyresparser | REJECT | Heavy spaCy / EN-centric |

## 4. REUSED COMPONENTS

| Source | Modules / patterns reused this pass |
|--------|-------------------------------------|
| JobRadar (GPL-3.0) | StepStone/XING: ItemList JSON-LD, article/card parse, stellenangebote /jobs/ link fallbacks, page=2 pagination (ideas adapted into `search/stepstone.py`, `search/xing.py`, `search/jsonld.py`) |
| AutoApply (MIT) | Prior Greenhouse/Lever/Ashby/Indeed/LinkedIn/Workday + browser (already in tree); this pass extended DE appliers with profile-field patterns consistent with AutoApply fill style |
| Auto-Fill-Forms | **Ideas only** (Personio DE labels / salary / consent) — no text or code copied |
| OpenResume / pyresparser | **None** (rejected) |

## 5. CURRENT CODE KEPT

- Entire PySide6 desktop shell, config model split, DB, matcher, location, salary, hard filter  
- BA + Indeed search, orchestration, dedup  
- Mature ATS appliers + `_maybe_submit` dry-run guard  
- Local CV parser + corpus fixtures  
- Packaging specs and GitHub workflows  

## 6. CURRENT CODE REMOVED

- Duplicate `LinkedInSearchSource` class body from `search/indeed.py` (now only in `search/linkedin.py`)  
- Overselling DE ATS as fully `supported` (moved to `PARTIALLY_SUPPORTED_ATS`)  

No wholesale subsystem deletion — Strangler replacements only where proven.

## 7. CUSTOM CODE ADDED

- `search/jsonld.py`: ItemList extraction + `job_from_list_card`  
- StepStone/XING HTML fallbacks + second page  
- `PARTIALLY_SUPPORTED_ATS` + `classify_ats_support` / coverage buckets  
- `BaseApplier._fill_german_profile_fields` (street/PLZ/Ort/Gehalt/Kündigung/Eintritt/consent)  
- Personio/SmartRecruiters/SuccessFactors wiring to German helpers + forced `needs_review`  
- Offline tests for ItemList, HTML cards, ATS partial classification  

Germany-specific rules (radius/remote/salary/profile) remain custom by design.

## 8. REGRESSION RESULTS

| Suite | Result |
|-------|--------|
| `pytest -q -m "not network"` (post-search) | 169 passed, 2 deselected |
| Same (post-ATS) | 169 passed, 2 deselected |
| CV corpus script | 10/10 PASS |
| CV parser/replace/sections tests | 39 passed |
| Shutdown / pause / Qt smoke | 10 passed |

## 9. REAL PACKAGED APP RESULTS

Linux cloud agent cannot open Windows EXE. Evidence deferred to GitHub Actions:

- Workflow: `.github/workflows/windows-smoke.yml`  
- Prior CI on this branch: run `34539000493` **success** (unit CI)  
- Windows Smoke: re-triggered after ATS push (`34539393931`); see Actions for artifact SHA256/size  

## 10. REAL SEARCH-ONLY RESULT

Offline contracts + monkeypatched HTML/JSON-LD paths prove StepStone card fallback and XING ItemList parsing. Live network search not run in this agent (policy: search-only; no live apply). Optional: `scripts/live_source_health.py` / `live-sources.yml`.

## 11. CV RESULT

10/10 fictional DE/EN corpus PASS. Replace A→B→C persistence tests PASS. **KEEP** local parser. Known historical leakage patterns remain locked by regression tests.

## 12. PREVIEW RESULT

Preview builder updated for `partially_supported` warning text; submit still only when `supported` + fully automatic + not dry_run. Existing preview unit tests remain green via full suite.

## 13. PAUSE/RESUME RESULT

`tests/test_pause_resume.py` PASS — automation flag / scheduler gate unchanged (KEEP).

## 14. CANCELLATION RESULT

Pipeline cancel + source timeout tests remain in green full suite (KEEP).

## 15. SHUTDOWN RESULT

`tests/test_shutdown.py` PASS (idempotent, cancel workers, close browsers). Transient Playwright task teardown noise only; no product regression.

## 16. GITHUB ACTIONS RESULT

- CI success on search commit: `34539000493`  
- CI + Windows Smoke re-run after ATS commit: see branch Actions for terminal status  

## 17. WINDOWS BUILD PATH

- Spec: `packaging/Jobhuntsaver.spec`  
- Local: `build.bat` (venv → pytest → PyInstaller)  
- CI: `.github/workflows/build-windows.yml` / `windows-smoke.yml`  
- Chromium on-demand under `%LOCALAPPDATA%\Jobhuntsaver\browsers`  

## 18. FILE SIZE

No new EXE built in this Linux environment. Spec SHA256:  
`f786a50d587a6ebf751e634df618025674cd9bad23c7b6c5efba93c5e08d1983` (`packaging/Jobhuntsaver.spec`)  
Site-packages audit (~1039 MB venv) documented in `docs/package-size-audit.md`. Packaged onefile historically ~160 MB class (Chromium not bundled).

## 19. SHA256

Packaged EXE SHA256: **not produced in this environment** — take from Windows Smoke / build artifact when workflow completes.

## 20. REMAINING TRUE EXTERNAL LIMITATIONS

- StepStone/XING HTML selectors can drift (sites change markup)  
- Live source blocks / CAPTCHA / rate limits outside our control  
- Workday/SuccessFactors multi-page login walls → needs_review by design  
- Taleo/iCIMS/Teamtailor/etc. detect-only until a proven adapter exists  
- Nominatim geocoding rate limits  
- Windows EXE open/shutdown proof depends on GitHub-hosted Windows runners  
- Auto-Fill-Forms remains unlicensed — cannot vendor playbook text  

## Philosophy check

Reuse was a tool, not the goal. Working subsystems were kept. Only StepStone/XING discovery and DE ATS honesty/hardening changed. CV, UI, browser, matcher, and packaging were not replaced.
