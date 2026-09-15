# Post-application lifecycle megapass — final report

**Feature branch:** `cursor/post-application-lifecycle-d85b`  
**PR:** https://github.com/deadfrogface/Karrierekrake/pull/17 (**MERGED** 2026-09-15T09:39:06Z)  
**Merged feature tip SHA:** `885de934d1ac4c455b807825255bd970a20f26ae`  
**Merge commit on main:** `e5096cb55fa9ff9d4c4f0ec6d1dd59d3e04503ee`  

## CI / Windows Smoke (PR #17 @ `885de93`)

| Check | Workflow | Result |
|-------|----------|--------|
| unit-tests | CI | **PASS** |
| privacy | CI | **PASS** |
| cv-regression | CI | **PASS** |
| database-migration-tests | CI | **PASS** |
| static-smoke | CI | **PASS** |
| qt-smoke | Windows Smoke | **PASS** |
| build-and-exe-smoke | Windows Smoke | **PASS** |

Runs: CI `34951457305`, Windows Smoke `34951457388`.

## Suite rollup

| Gate | Result |
|------|--------|
| Full local pytest `-m "not network"` | **PASS** (356 passed, 2 deselected) |
| CI (all jobs) | **PASS** |
| Windows Smoke (qt + EXE) | **PASS** |

## Reuse counts

| Kind | Count | Notes |
|------|------:|-------|
| Upstream repos audited | 8 | Source + LICENSE inspected |
| COPY / COPY→ADAPT | 2 | ICS; classifier/ATS pattern sets |
| ADAPT | 18 | See audit matrix |
| REFERENCE | 6 | STATUS_RANK, exclude rules, UI ideas |
| REJECT | 8 | Commons Clause; Claude; Django/React/Gradio core; company blacklist-as-ban; required ML |
| EXISTING Karrierekrake reused | 5 | has_applied, detector, matcher evidence, apps UI, dedup |
| ORIGINAL after reuse | 5 | FreeBusy wrapper, SendGate, ApplicationCase schema, case_pipeline, secure token file fallback |

Audit: `docs/post-application-lifecycle-reuse-audit.md`  
Snapshots: `third_party/post-application-audit/`

## Critical test matrix

| Scenario | Result | Evidence |
|----------|--------|----------|
| Rejection → search must not rediscover same vacancy | **PASS** | `test_rejection_suppresses_same_vacancy_across_sources` |
| Interview → search suppression | **PASS** | `test_interview_status_suppresses_search_rediscovery` |
| Cross-source same job (URL identity) | **PASS** | Indeed jk= twin in rejection suppress test |
| Same company, different job NOT blacklisted | **PASS** | `test_rejection_does_not_suppress_different_job_same_company` |
| Ambiguous email association → review | **PASS** | `test_ambiguous_association_when_two_cases_share_domain` |
| False rejection protection | **PASS** | `test_false_rejection_guard_does_not_force_rejected` |
| Calendar busy + working-hours conflict | **PASS** | `test_calendar_working_hours_and_busy_conflict` |
| Send failure safety (draft kept) | **PASS** | `test_send_failure_keeps_draft_and_records_error` |
| Draft-only default / no auto-send | **PASS** | `test_draft_only_default_blocks_send`, follow-up `auto_send=0` |
| Token restart survival | **PASS** | `test_token_roundtrip_survives_restart` |
| Manager defense-in-depth refuse re-apply | **PASS** | `test_manager_refuses_known_case_even_without_job_row` |
| Fictional corpus classification | **PASS** | `test_corpus_classification_matches_expectations` |
| Full pytest `-m "not network"` | **PASS** | 356 passed, 2 deselected |
| Privacy scan | **PASS** | `scripts/privacy_scan.py` OK |
| NOTICE / third-party licenses | **PASS** | NOTICE updated; Commons Clause not copied |

## Phase delivery

| Phase | Status |
|-------|--------|
| 0 Audit before code | **PASS** (committed first) |
| A ApplicationCase foundation | **PASS** |
| B Known-job suppression | **PASS** |
| C Contact preference + phone windows (config) | **PASS** (settings YAML + Settings UI) |
| D Gmail OAuth readonly + secure tokens | **PASS** (optional google libs) |
| E Email filter/classify + confidence | **PASS** |
| F Association + ambiguous review UI | **PASS** |
| G Rejection/offer/interview events | **PASS** |
| H Timeline/dashboard/tasks | **PASS** (lifecycle page + tasks) |
| I Calendar availability + ICS | **PASS** (FreeBusy helper local; ICS export) |
| J Reply draft + approval gate | **PASS** |
| K Interview prep from evidence | **PASS** |
| L Follow-up/ghosted suggest-only | **PASS** |
| M Hostile tests + fictional corpus | **PASS** |

## Remaining limitations

- Live Gmail/Calendar OAuth requires user-provided `private/gmail_credentials.json` and optional google/keyring packages; not exercised against real Google accounts in CI (API libs optional).
- Google Calendar FreeBusy is implemented as local collision helpers; live FreeBusy API client is gated behind `calendar_freebusy_enabled` and needs OAuth calendar scope when wired for production use.

## Safety preserved

Dry-run / submit gate, CV role hard-block, evidence matching, no CAPTCHA bypass, no real employer send without approval, no company-wide blacklist on single vacancy rejection, no cloud paid AI.
