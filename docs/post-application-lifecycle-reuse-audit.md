# Post-application lifecycle — REUSE MATRIX / AUDIT

**Date:** 2026-09-15  
**Branch:** `cursor/post-application-lifecycle-d85b`  
**Rule:** No product implementation until this audit is committed.  
**Snapshots:** `third_party/post-application-audit/` (licensed originals for COPY/ADAPT; REJECT sources license-only)

Karrierekrake already has: SQLite `jobs`/`applications`, `has_applied` twin blocking, ATS URL detect (`apply/detector.py`), PySide6 Applications page, dry-run submit gate, local matcher evidence (DIRECT/RELATED/NOT_SUPPORTED). Missing: ApplicationCase lifecycle beyond apply, Gmail intelligence, email→case association, calendar availability, reply drafts, follow-up/ghosted, global known-job search suppression.

---

## Upstream inventory (actual LICENSE files verified)

| # | Repo | License | Stack / constraint | Verdict summary |
|---|------|---------|--------------------|-----------------|
| 1 | [MadGapun/PBP](https://github.com/MadGapun/PBP) | **MIT** | Python DE lifecycle; optional Claude/Ollama | **PRIMARY ADAPT** for DE email status, association, ICS, follow-up text, job state, meeting collision |
| 2 | [cyberthreatgurl/GmailJobTracker](https://github.com/cyberthreatgurl/GmailJobTracker) | **MIT** | Django + Gmail API + regex/ML | **PRIMARY COPY/ADAPT** for Gmail readonly OAuth, rule classifier, company/ATS from mail, patterns; **REJECT** Django/ML stack as core dep |
| 3 | [Ralph-Abejuela/ejobtrack](https://github.com/Ralph-Abejuela/ejobtrack) | **Apache-2.0** | Vite/TS + Gmail client + Xenova transformers | **ADAPT** Gmail list/get/parse; **REJECT** browser ML model as required dep |
| 4 | [AkhilDhawan22/job-track-os](https://github.com/AkhilDhawan22/job-track-os) | **MIT + Commons Clause** | Node, Sheets, Slack, LLM | **REJECT COPY** (Commons Clause). Reference ideas only in prose |
| 5 | [thehar/job-tracker](https://github.com/thehar/job-tracker) | **MIT** | Vanilla JS PWA | **ADAPT** reminder/calendar event-shape patterns; no backend |
| 6 | [Tomiwajin/CareerSync](https://github.com/Tomiwajin/CareerSync) | **MIT** | Next.js + Gradio HF + Gmail | **REFERENCE** exclude-email rules; **REJECT** Gradio/cloud classify + React UI |
| 7 | [yigitcankzl/trackjobapplications](https://github.com/yigitcankzl/trackjobapplications) | **MIT** | Django + React | **ADAPT** status enum / follow-up heuristics / Google Calendar URL builder; **REJECT** Django/React as new core |
| 8 | [lbwalton/ai-job-tracker](https://github.com/lbwalton/ai-job-tracker) | **MIT** | Next.js + **Claude** Gmail classify | **REJECT** Claude/Anthropic path. **REFERENCE** STATUS_RANK, ambiguous review inbox, ATS sender domains |

Clone evidence: shallow clones under `/tmp/reuse-audit/` (2026-09-15). Snapshots of copyable files under `third_party/post-application-audit/`.

---

## Component matrix (required coverage)

Legend: **COPY** = vendor/adapt with attribution · **ADAPT** = rewrite into Karrierekrake types using algorithms · **REFERENCE** = design only · **REJECT** = do not use · **EXISTING** = already in Karrierekrake · **ORIGINAL** = write new after reuse exhausted

| Component | Decision | Source file / function | License | Why | Original saved |
|-----------|----------|------------------------|---------|-----|----------------|
| **Gmail OAuth (readonly)** | **ADAPT** | GmailJobTracker `gmail_auth.py` `get_gmail_service`, SCOPES=`gmail.readonly`; ai-job-tracker `gmail.ts` `buildAuthUrl`/`exchangeCode` (token refresh shape) | MIT | Proven local installed-app OAuth + refresh; pickle→secure Windows cred store | `third_party/.../GmailJobTracker/gmail_auth.py`, `ai-job-tracker/gmail_readonly_excerpt.ts` |
| **Gmail sync (list/get)** | **ADAPT** | ejobtrack `gmail.ts` `listMessages`/`getMessage`/`parseMessage`/`fetchWithRetry`; GmailJobTracker parser payload walk | Apache-2.0 / MIT | Clean TS client → port to Python `google-api-python-client` already pattern-compatible; 401/429 handling | `ejobtrack/gmail.ts`, `GmailJobTracker/email_parser.py` |
| **Email prefilter** | **ADAPT** + **REFERENCE** | CareerSync `shouldExcludeEmail`; GmailJobTracker noise early-detect + `NOISE_SUBTYPES`; Gmail query filters | MIT | Domain/exact/wildcard exclude without ML; noise short-circuit before company extract | `CareerSync/email-utils.ts`, `rule_classifier.py` |
| **Email normalization** | **ADAPT** | PBP `email_service.py` `_html_to_plaintext`, `_get_text_parts`, `strip_quoted_reply`, `parse_eml`; GmailJobTracker `EmailBodyParser` | MIT | DE-friendly MIME/HTML→text; strip quotes before classify | `PBP/email_service.py`, `GmailJobTracker/email_parser.py` |
| **ATS recognition (from email)** | **ADAPT** + **EXISTING** | GmailJobTracker `scripts/ats_detection_heuristics.py` URL patterns; `CompanyResolver.extract_from_ats_sender`; Karrierekrake `apply/detector.py` for job URLs | MIT / existing | Extend fingerprints for *mail* senders/bodies; keep URL detector for apply path | `ats_detection_heuristics.py`, `company_resolver.py` |
| **Company extraction / normalization** | **ADAPT** | GmailJobTracker `CompanyResolver` / `CompanyValidator.normalize_company_name`; PBP `duplicate_detection.normalize_company_name`; Karrierekrake `core.text_normalize.clean_company` | MIT / existing | Tiered extract (ATS sender → domain map → subject); merge with existing `company_key` | `company_resolver.py`, `PBP/duplicate_detection.py` |
| **Email classification** (rejection / interview / offer / confirmation) | **ADAPT** | **PBP** `detect_email_status` + `STATUS_PATTERNS` (DE+EN); **GmailJobTracker** `RuleClassifier` + `json/patterns.json` (EN rich); ai-job-tracker categories **REFERENCE only** | MIT | Local regex/phrase rules + confidence; **no** Claude/OpenAI/Gemini; **no** Django ML / Xenova as required | `PBP/email_service.py`, `rule_classifier.py`, `patterns.json` |
| **False-rejection protection** | **ADAPT** | GmailJobTracker early `rejection_override`, cancelled-position helpers (`parser_helpers.is_cancelled_position`); PBP multi-hit confidence | MIT | Require strong rejection cues; interview/scheduling language overrides weak “not selected” noise | `parser_helpers.py`, `rule_classifier.py` |
| **Email → ApplicationCase association** | **ADAPT** | PBP `match_email_to_application` (domain signal + 0.90 threshold + recruiter ambiguity); GmailJobTracker `_application_identity_matches` / job_id+title | MIT | “Im Zweifel unverknüpft”; ambiguous → review UI | `PBP/email_service.py`, `parser_association_excerpt.py` |
| **Cross-source dedup / known-job suppression** | **ADAPT** + **EXISTING** + **ORIGINAL** | PBP `stellen_zustand` / `stellen_dublette` / `find_repost_of_application`; Karrierekrake `deduplicator` + `has_applied` | MIT / existing | Suppress rediscovery of applied/rejected/interview/etc. globally; **never** company-wide blacklist on one vacancy | `stellen_zustand.py`, `duplicate_detection.py` |
| **Lifecycle / ApplicationCase foundation** | **ADAPT** + **ORIGINAL** | trackjobapplications status enum; ai-job-tracker `STATUS_RANK` / `TERMINAL_STATUSES` (**REFERENCE**); PBP `stellen_zustand`; extend Karrierekrake `ApplicationRecord`/`JobStatus` | MIT | New case model + event timeline on SQLite; rank prevents auto-downgrade | `applicationStatus.ts`, `ai-job-tracker/core-index.ts`, `stellen_zustand.py` |
| **Timeline / dashboard / tasks** | **ADAPT** + **EXISTING** | PBP dashboard task/nachfass ideas; trackjob detail timelines (**REFERENCE** UI); Karrierekrake dashboard/applications pages | MIT | Extend PySide6 pages; no React/Next | snapshots + existing `desktop/pages/` |
| **Follow-up / ghosted** | **ADAPT** | PBP `nachfass_text` / `ist_ueberholt` / `dringlichkeit` (**strip** `claude_prompt`); trackjob `needsFollowUp`; GmailJobTracker ghosted label patterns | MIT | Suggest-only tasks; **never** auto-send | `nachfass_text.py`, `followUp.ts` |
| **Calendar availability / collision** | **ADAPT** | PBP `termin_dubletten` (`finde_dublette`, phantom meetings); thehar `CalendarIntegration` settings shape | MIT | Collision vs user working hours + known interviews; **no** private event titles to employers | `termin_dubletten.py`, `calendar-integration.js` |
| **ICS export** | **COPY/ADAPT** | PBP `ics_service.py` (`ics_escape`, `ics_fold`, `build_meetings_ics`) | MIT | Small, correct RFC5545 fold/escape | `PBP/ics_service.py` |
| **Reminders** | **ADAPT** | thehar `notifications.js` reminder scheduler; trackjob calendar URL builder | MIT | Local desktop reminders / task list; optional GCal *availability* block only | `notifications.js`, `calendar.ts` |
| **Google Calendar (availability only)** | **ORIGINAL** + **REFERENCE** | OAuth calendar.readonly freebusy; ai-job-tracker/thehar only for “sync interviews” concept — **reject** exporting private titles | MIT patterns | New thin FreeBusy client; never send busy titles to employers | — |
| **Reply drafting + approval-before-send** | **ORIGINAL** + **ADAPT** | PBP `nachfass_text` templates (local); reject cloud AI; draft-only default | MIT templates | Template drafts + explicit user send approval; send-failure safety | `nachfass_text.py` |
| **Interview prep (evidence reuse)** | **EXISTING** + **ORIGINAL** | Karrierekrake matcher `evidence` DIRECT/RELATED/NOT_SUPPORTED; PBP `interview_vollstaendigkeit` **REFERENCE** | existing / MIT | Wrap evidence into prep checklist UI; no LLM | — |
| **Contact preference + telephone availability** | **ORIGINAL** + **REFERENCE** | PBP `kontakt_pflicht`; config in `SettingsConfig` | MIT ideas | Configurable preference + availability windows; **no** hardcoded phone policy | — |
| **Defense-in-depth re-apply refuse** | **EXISTING** + **ORIGINAL** | `ApplicationManager.can_auto_apply` / `has_applied` → also check ApplicationCase known statuses | existing | Even if search dedup fails, manager refuses known cases | — |

---

## Per-repo deep notes (source inspected, not README-only)

### 1. PBP (MIT) — HIGH

| Path | Role | Reuse |
|------|------|-------|
| `services/email_service.py` | DE status phrases, association, ICS-from-mail, rejection feedback | **ADAPT** core |
| `services/ics_service.py` | ICS build/escape/fold | **COPY→ADAPT** |
| `services/stellen_zustand.py` | Job state: aktiv/aussortiert/beworben | **ADAPT** for known-job messaging |
| `services/nachfass_text.py` | Follow-up copy + overdue supersession | **ADAPT**; **REJECT** `claude_prompt` |
| `services/termin_dubletten.py` | Meeting collision / phantom appointments | **ADAPT** |
| `duplicate_detection.py` | Company normalize + repost-of-application | **ADAPT** |
| `services/blacklist_regel.py` | Company/keyword blacklist | **REJECT** for “one rejection ⇒ company ban”; may **REFERENCE** exception/title-scoped rules only |
| `services/ats_firmen.py` | Live ATS slug probing | **REJECT** (network probe / out of scope) |
| Claude/Ollama MCP stack | AI assistant | **REJECT** as core |

### 2. GmailJobTracker (MIT) — HIGH

| Path | Role | Reuse |
|------|------|-------|
| `gmail_auth.py` | Local OAuth readonly + token refresh | **ADAPT**; replace pickle with encrypted/Windows credential store |
| `rule_classifier.py` + `json/patterns.json` | Regex labels + excludes + early detection | **ADAPT**; extend with PBP DE phrases |
| `email_parser.py` | Gmail MIME / HTML / ICS organizer | **ADAPT** (drop Django timezone) |
| `company_resolver.py` | ATS sender/body/subject company extract | **ADAPT** (trim to offline rules; no Django models) |
| `parser.py` association helpers | job_id/title identity | **ADAPT** excerpt |
| `ml_subject_classifier.py` / Django dashboard | TF-IDF + web UI | **REJECT** as required dependency |
| `scripts/ats_detection_heuristics.py` | ATS URL regex list | **ADAPT** into detector fingerprints |

### 3. ejobtrack (Apache-2.0)

| Path | Role | Reuse |
|------|------|-------|
| `src/lib/gmail.ts` | list/get/parse, 401 refresh, 429 | **ADAPT** to Python |
| `src/lib/classify-email.ts` | Xenova `job-tracker-email-classifier` | **REJECT** required ML download; optional later only if offline+license clear |

### 4. job-track-os (MIT + Commons Clause)

**REJECT COPY** of all source. Inspected: `gmailAuth.js` readonly scope, `gmail.js` `classify`/`matchJobByCompany`. Patterns may inform design notes only; no code in tree beyond `LICENSE` + `REJECT.txt`.

### 5. thehar/job-tracker (MIT)

| Path | Role | Reuse |
|------|------|-------|
| `js/calendar-integration.js` | Provider settings, event duration/reminders | **ADAPT** concepts |
| `js/notifications.js` | Local follow-up/interview reminders | **ADAPT** |
| CRUD PWA / IndexedDB | Tracker UI | **REFERENCE** only (we have PySide6) |

### 6. CareerSync (MIT)

| Path | Role | Reuse |
|------|------|-------|
| `lib/email-utils.ts` `shouldExcludeEmail` | Exclude list | **ADAPT** |
| `app/api/process-emails` Gradio HF | Cloud classify | **REJECT** |

### 7. trackjobapplications (MIT)

| Path | Role | Reuse |
|------|------|-------|
| `applicationStatus.ts` / Django `STATUS_CHOICES` | Lifecycle states | **ADAPT** into ApplicationCase |
| `followUp.ts` `needsFollowUp` | Simple staleness | **ADAPT** (configurable days) |
| `calendar.ts` `buildGoogleCalendarUrl` | Template link | **ADAPT** optional |
| React/Django backend | Full stack | **REJECT** as new core deps |

### 8. ai-job-tracker / JobTrackr (MIT)

| Path | Role | Reuse |
|------|------|-------|
| `packages/core` `STATUS_RANK`, `CATEGORY_TO_STATUS`, `EMAIL_CATEGORIES` | Taxonomy | **REFERENCE** (reimplement locally without Zod/Claude) |
| `apps/web/src/lib/gmail.ts` ATS_DOMAINS + OAuth | Readonly Gmail | **REFERENCE**; classification calls Claude → **REJECT** |
| Ambiguous review inbox pattern | UX | **REFERENCE** → PySide6 review queue |

---

## Karrierekrake gap → planned modules (post-audit only)

| Phase | Module (planned) | Primary reuse |
|-------|------------------|---------------|
| A | `core/lifecycle.py` ApplicationCase + events | trackjob status + PBP zustand + STATUS_RANK idea |
| B | `core/known_jobs.py` + search/manager hooks | PBP stellen_zustand + existing dedup/has_applied |
| C | Settings: contact preference, phone windows | ORIGINAL + PBP kontakt ideas |
| D | `integrations/gmail_auth.py` + secure token store | GmailJobTracker + Windows DPAPI/keyring |
| E | `integrations/email_classify.py` | PBP STATUS_PATTERNS + GJT RuleClassifier |
| F | `integrations/email_associate.py` + review UI | PBP match_email_to_application |
| G | Case event writers (reject/offer/interview) | Classifier + false-reject guards |
| H | Timeline/tasks UI | Extend desktop pages |
| I | Calendar freebusy + ICS | PBP ics + ORIGINAL freebusy |
| J | Draft reply + approval send | PBP nachfass templates; draft-only default |
| K | Interview prep from matcher evidence | EXISTING evidence |
| L | Follow-up/ghosted suggestions | PBP nachfass + trackjob needsFollowUp |
| M | Fictional corpus + hostile tests | ORIGINAL fixtures |

**Hard constraints preserved:** dry-run, submit gate, CV roles, evidence matching, privacy scan, no CAPTCHA bypass, no real external job submit in tests, no real employer send without approval, no company-wide blacklist on single vacancy rejection.

---

## Reuse counts (audit phase)

| Classification | Count (component rows) |
|----------------|------------------------|
| Audited upstream repos | **8** |
| COPY / COPY→ADAPT candidates | **2** (ICS; selected classifier patterns/heuristics) |
| ADAPT | **18** |
| REFERENCE | **6** |
| REJECT | **8** (Commons Clause whole repo; Claude classify; Django/React/Gradio/Xenova as core; company blacklist-as-ban; live ATS probing; ML required path) |
| EXISTING Karrierekrake | **5** |
| ORIGINAL (after reuse) | **5** |

Exact line-level COPY vs rewrite will be recorded in NOTICE when integrated.

---

## NOTICE / license plan (on integrate)

- MIT (PBP, GmailJobTracker, thehar, CareerSync snippet, trackjob snippets, ai-job-tracker taxonomy ideas): retain copyright + MIT permission notice in `NOTICE`.
- Apache-2.0 (ejobtrack Gmail client patterns): Apache notice + LICENSE reference.
- Commons Clause (job-track-os): **no code**.
- Do not vendor Django, React, Next, Postgres, Sheets, Slack, Claude SDK, OpenAI, Gemini.

---

## Explicit non-goals from this audit

- No CAPTCHA bypass from any source.
- No auto-send of employer email.
- No cloud paid AI.
- No blacklisting entire companies because one vacancy was rejected.
- No importing PBP Claude MCP / GmailJobTracker Django app as runtime.

---

## Audit gate

**STATUS: COMPLETE.** Implementation of phases A→M may begin only after this file is committed to the branch.
