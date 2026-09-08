# Jobhuntsaver — Source Analysis (Phase 0)

Analyzed repositories (cloned to `/tmp/refs/` for reference only; not vendored wholesale):

| Project | URL | License | Verified |
|---------|-----|---------|----------|
| JobRadar | https://github.com/jason-huanghao/jobradar | **GPL-3.0** | Yes (`LICENSE` = GNU GPL v3) |
| AutoApply | https://github.com/AbhishekMandapmalvi/AutoApply | **MIT** | Yes (`LICENSE` = MIT) |
| Jobhuntsaver (target) | https://github.com/deadfrogface/Jobhuntsaver | **GPL-3.0** (chosen) | Empty at analysis time |

**License decision:** Jobhuntsaver is GPL-3.0 so JobRadar-derived adapters can be reused legally. AutoApply MIT code is compatible with attribution in `NOTICE`.

---

## Feature reuse matrix

| Feature | Source project | File / function | Current status | Reuse? | Modify? | Build new? |
|---------|----------------|-----------------|----------------|--------|---------|------------|
| BA Jobsuche REST API | JobRadar | `sources/adapters/arbeitsagentur.py` `ArbeitsagenturSource` | JobRadar used v4 list; **Jobhuntsaver updated to public v6 list + v4 jobdetails (base64 refnr)** | Yes | Yes → Job model + v6 | No |
| Indeed / Google / LinkedIn search via JobSpy | JobRadar | `sources/adapters/jobspy_adapter.py` | Library wrapper; DE via `country_indeed=germany` | Yes (optional) | Yes | Thin adapter |
| StepStone scrape | JobRadar | `sources/adapters/stepstone.py` | HTML/JSON-LD scraper | Yes | Yes | Later harden |
| XING scrape | JobRadar | `sources/adapters/xing.py` | HTML/JSON-LD scraper | Yes | Yes | Later harden |
| CN sources (Boss/Lagou/Zhilian) | JobRadar | `adapters/bosszhipin.py` etc. | CN-only | **No** | — | — |
| Raw job model | JobRadar | `models/job.py` `RawJob` | Too narrow vs Spec §5 | No (reference) | — | **Yes** `core/models.py` |
| URL dedup ID | JobRadar | `sources/normalizer.py` | URL/sha256 only | Partial | Yes | Extended dedup |
| Hard keyword/company/age filter | JobRadar | `scoring/hard_filter.py` | Local, works | Yes (pattern) | Yes + distance | — |
| LLM job scoring | JobRadar | `scoring/scorer.py` + `llm/` | **Requires LLM API** | **No** (forbidden as core) | — | **Yes** local matcher |
| LLM CV extract | JobRadar | `profile/extractor.py` | LLM | **No** as required path | — | PDF/DOCX parse |
| Apply BOSS/LinkedIn | JobRadar | `apply/` | Limited / CN | **No** | — | Use AutoApply |
| FastAPI / OpenClaw UI | JobRadar | `api/`, skill | Not needed | **No** | — | Streamlit |
| Apply base + retry/CAPTCHA | AutoApply | `bot/apply/base.py` | Solid | Yes | Yes (our types) | — |
| Greenhouse applier | AutoApply | `bot/apply/greenhouse.py` | Form fill + upload | Yes | Yes | — |
| Lever applier | AutoApply | `bot/apply/lever.py` | Form fill + upload | Yes | Yes | — |
| Ashby applier | AutoApply | `bot/apply/ashby.py` | Present | Yes | Yes | — |
| Indeed applier | AutoApply | `bot/apply/indeed.py` | Present | Yes | Yes | — |
| LinkedIn applier | AutoApply | `bot/apply/linkedin.py` | Present | Yes | Yes | — |
| Workday applier | AutoApply | `bot/apply/workday.py` | Largest/most complex | Yes | Yes | — |
| Browser persistent profile | AutoApply | `bot/browser.py` | Playwright persistent | Yes | Yes paths | — |
| ATS URL detect | AutoApply | `core/filter.py` `detect_ats` | Missing DE ATS | Yes | Extend | Personio etc. |
| Local score 0–100 | AutoApply | `core/filter.py` `score_job` | No km distance | Yes (basis) | Heavy | Distance bands |
| Review / login gates | AutoApply | `bot/state.py` | Thread gates | Concepts | Adapt | Run manager |
| Bot main loop | AutoApply | `bot/bot.py` | Continuous + LLM docs | Ideas only | — | `app/main.py` |
| Document text extract | AutoApply | `core/document_parser.py` | PDF/DOCX/TXT | Yes | pypdf | — |
| MD resume parse | AutoApply | `core/resume_parser.py` | Markdown sections | Partial | Adapt | CV pipeline |
| Electron / Flask / SocketIO | AutoApply | `shell/`, `routes/`, `app.py` | Desktop UI | **No** | — | Streamlit |
| AI engine / LaTeX resume | AutoApply | `core/ai_engine.py` etc. | LLM-heavy | **No** as required | — | Template CL |
| Personio adapter | — | — | Missing | — | — | **Yes** Phase 9 |
| SmartRecruiters / SuccessFactors | — | — | Missing | — | — | **Yes** Phase 9 |
| Haversine + geocode cache | — | — | Missing | — | — | **Yes** Phase 3 |
| SQLite jobs/applications schema | both have DBs | different schemas | Reference | — | — | **Yes** Spec §17 |
| Streamlit dashboard | — | — | — | — | — | **Yes** Phase 5 |
| Windows Task Scheduler | — | JobRadar has macOS agent | — | — | — | **Yes** Phase 10 |

---

## Exact vendor / adapt list

### From JobRadar (GPL-3.0) — adapt into Jobhuntsaver

1. `arbeitsagentur.py` → `search/bundesagentur.py` (map to our `Job`)
2. Ideas from `jobspy_adapter.py` → `search/indeed.py` / LinkedIn search via JobSpy
3. Ideas from `stepstone.py`, `xing.py` → `search/stepstone.py`, `search/xing.py`
4. Pattern from `hard_filter.py` → `core/hard_filter.py`
5. Pattern from `normalizer.py` → part of `core/deduplicator.py`

### From AutoApply (MIT) — adapt into Jobhuntsaver

1. `bot/apply/base.py` → `apply/base.py`
2. `bot/apply/{greenhouse,lever,ashby,indeed,linkedin,workday}.py` → `apply/`
3. `bot/browser.py` → `browser/browser_manager.py`
4. `detect_ats` / scoring ideas from `core/filter.py` → `apply/detector.py`, `core/matcher.py`
5. `core/document_parser.py` → `core/cv_parser.py` (text extract)

### Explicitly NOT copied

- JobRadar LLM stack, FastAPI UI, CN scrapers, OpenClaw skill
- AutoApply Electron shell, Flask/SocketIO frontend, `ai_engine`, LaTeX resume compiler

---

## Implementation mapping (Jobhuntsaver modules)

| Jobhuntsaver module | Primary origin | Notes |
|---------------------|----------------|-------|
| `search/bundesagentur.py` | JobRadar BA adapter | Highest priority DE source |
| `search/indeed.py` | JobRadar JobSpy | Germany country |
| `search/linkedin.py` | JobRadar JobSpy / AutoApply search | Session-aware later |
| `search/stepstone.py` | JobRadar StepStone | Discovery only first |
| `search/xing.py` | JobRadar XING | Discovery only first |
| `core/matcher.py` | AutoApply `score_job` + new distance | No LLM |
| `core/location.py` | New | Nominatim + Haversine + SQLite cache |
| `apply/*` | AutoApply appliers | + Personio/StepStone later |
| `ui/app.py` | New Streamlit | Replace Electron/FastAPI |
| `app/main.py` | New pipeline | Modes: search_only / review / full |

---

## Verification notes

- JobRadar README claims AI scoring and multi-source crawl; **scoring code confirms LLM dependency** — cannot be core for Jobhuntsaver.
- Arbeitsagentur adapter uses documented public Jobsuche REST endpoint — preferred over browser automation.
- AutoApply Greenhouse/Lever are short, selector-based Playwright fillers suitable for adaptation.
- AutoApply Workday is larger (~431 lines) — reuse carefully; expect `needs_review` fallbacks.
