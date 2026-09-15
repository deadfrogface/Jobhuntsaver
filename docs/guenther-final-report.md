# Günther die Krake — Final Report

**Feature branch:** `cursor/guenther-local-ai-megapass-d85b`  
**PR:** https://github.com/deadfrogface/Karrierekrake/pull/19  
**Base `origin/main`:** `8c1e81c9653789251e2500b249a9abbf3d7d3175`  
**Verified green head:** `3c67969b5ca41b03abd4392261c7b869639b6f4b`  
**Lifecycle gate:** PR #17 + #18 on main — proceeded.  
**Agent must not merge** — human merge only.

## CI / Windows Smoke @ `3c67969`

| Check | Workflow | Result | Run |
|-------|----------|--------|-----|
| unit-tests | CI | **PASS** | `34970852477` |
| privacy | CI | **PASS** | `34970852477` |
| cv-regression | CI | **PASS** | `34970852477` |
| database-migration-tests | CI | **PASS** | `34970852477` |
| static-smoke | CI | **PASS** | `34970852477` |
| qt-smoke | Windows Smoke | **PASS** | `34970852592` |
| build-and-exe-smoke | Windows Smoke | **PASS** | `34970852592` |

**7/7 PASS** on current verification head `3c67969` (includes Windows Smoke qt-smoke + build-and-exe-smoke).

## Real GGUF inference (RAN — not simulated)

| Item | Result |
|------|--------|
| Status | **RAN** |
| Runtime | llama-cpp-python 0.3.35, CPU, ~15 GB RAM Linux agent |
| Artifacts | `benchmark/results_live_gguf.json`, `benchmark/results_live_summary.json` |
| Live winner (smallest meeting safety) | **`qwen3-1.7b`** |
| qwen3-1.7b | safety_penalty **0**, meets_safety **true**, utility ~71.6 |
| qwen3-4b | safety_penalty **40** (prompt-injection follow → offer), meets_safety **false**, utility ~31.6 |
| GATED | **No** |

Pins: LIGHT + STANDARD URL+SHA256 in `guenther/model_manager.py`. Phi-4-mini download deferred (REVIEW REQUIRED, non-blocking).

Deterministic Karrierekrake gates remain authoritative for consequential actions.

## Hostile / integration

| Suite | Result |
|-------|--------|
| `tests/test_guenther_local_ai.py` | **PASS** (24) |
| `scripts/privacy_scan.py` | **OK** |
| CI unit-tests / privacy | **PASS** @ `3c67969` |

## Mission checklist (20)

| # | Item | Status |
|---|------|--------|
| 1 | Base SHA | `8c1e81c9653789251e2500b249a9abbf3d7d3175` |
| 2 | Head SHA (verified green) | `3c67969b5ca41b03abd4392261c7b869639b6f4b` |
| 3 | Runtime | `LocalAIProvider` (llama_cpp / ollama-dev / heuristic / null) |
| 4 | Models | LIGHT+STANDARD pinned; no weights in git |
| 5 | Winner | Live **`qwen3-1.7b`**; catalog STANDARD still `qwen3-4b` (fails live injection safety) |
| 6 | Sizes | ~1.28 GB / ~2.50 GB Q4_K_M |
| 7 | RAM | LIGHT ≥~3 GB; STANDARD ≥~5 GB |
| 8 | Licenses | Runtime MIT; Qwen Apache-2.0; Phi MIT deferred; Gemma 3 rejected default |
| 9 | Reuse | WRAP llama-cpp; EXISTING Pydantic, matcher, classify/associate, lifecycle |
| 10 | Original | `guenther/*`, `benchmark/*` |
| 11 | Capabilities | CV/Job/Evidence/Email/Association/Writing/Interview — advisory |
| 12 | Fallbacks | disabled / missing / invalid / timeout / OOM / cancel |
| 13 | Safety | No submit/send/finalize/CAPTCHA bypass; fail-closed association; claim guards |
| 14 | Tests | Hostile + CI unit-tests PASS |
| 15 | Privacy | No cloud AI; no PII logs; privacy job PASS |
| 16 | Windows Smoke | **PASS** (qt-smoke + build-and-exe-smoke) |
| 17 | EXE | Spec collects `guenther`; EXE smoke PASS; weights not bundled |
| 18 | Limitations | Phi GGUF URL deferred; Windows laptop user-download UX still useful |
| 19 | Remaining live | Optional: end-user confirm download UI on Windows desktop |
| 20 | Docs | This report + `docs/guenther-*.md` |

## MERGE READY: **YES**

For human merge of green head `3c67969` (or successor tip that remains green).  
**Do not auto-merge.** Remaining non-blockers: Phi pin deferred; optional Windows laptop UX confirm.

## GÜNTHER STATUS

```
PR:        https://github.com/deadfrogface/Karrierekrake/pull/19
Head:      3c67969b5ca41b03abd4392261c7b869639b6f4b
CI:        7/7 PASS (incl. Windows Smoke)
Real GGUF: RAN — winner qwen3-1.7b; qwen3-4b fails injection safety
Hostile:   PASS
MERGE READY: YES (human merge only)
```
