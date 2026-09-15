# Günther die Krake — Final Report

**Feature branch:** `cursor/guenther-local-ai-megapass-d85b`  
**PR:** https://github.com/deadfrogface/Karrierekrake/pull/19  
**Base `origin/main`:** `8c1e81c9653789251e2500b249a9abbf3d7d3175`  
**Head SHA:** branch tip of `cursor/guenther-local-ai-megapass-d85b`  
**Lifecycle gate:** PR #17 + #18 present on main — **proceeded** (not blocked).  
**PR title:** `feat(ai): Günther local intelligence — offline CV, job, mail & interview AI`  
**Do not merge** until CI/Windows Smoke green + review.

## Mission checklist (20 items)

| # | Item | Status |
|---|------|--------|
| 1 | Base SHA | `8c1e81c9653789251e2500b249a9abbf3d7d3175` |
| 2 | Head SHA | branch tip (`git rev-parse`) |
| 3 | Runtime | Abstract `LocalAIProvider`; primary WRAP `llama-cpp-python` (optional); Ollama optional dev; heuristic/null fail-closed |
| 4 | Models catalog | Qwen3 1.7B, Qwen3 4B pinned; Phi-4-mini deferred REVIEW REQUIRED — **no weights in git** |
| 5 | Winner | Product Autopick STANDARD=`qwen3-4b`, LIGHT=`qwen3-1.7b`; CI baseline=`heuristic-local` |
| 6 | Sizes | LIGHT ~1.28 GB; STANDARD ~2.50 GB (Q4_K_M) |
| 7 | RAM | LIGHT ≥~3 GB; STANDARD ≥~5 GB; detect via hardware tiers |
| 8 | Licenses | Runtime MIT; Qwen Apache-2.0; Phi MIT (deferred); Gemma 3 rejected as default |
| 9 | Reuse | WRAP llama.cpp/python; EXISTING Pydantic, matcher, classify/associate, lifecycle |
| 10 | Original | provider abstraction, validation, model manager, prompts, service, benchmark |
| 11 | Capabilities | CV/Job/Evidence/Email/Association/Writing/Interview — advisory |
| 12 | Fallbacks | disabled / not installed / missing model / invalid / timeout / OOM / cancel |
| 13 | Safety | No submit/send/finalize/CAPTCHA; no silent HIGH assoc; false-reject guard; claim guards |
| 14 | Tests | `tests/test_guenther_local_ai.py` + full offline suite regression |
| 15 | Privacy | No cloud fallback; no PII keys in logs; AppData models |
| 16 | Windows Smoke | Pending / see PR checks |
| 17 | EXE | Spec collects `guenther`; weights not bundled |
| 18 | Limitations | Live GGUF inference not run in CI; Phi download deferred |
| 19 | Remaining live tests | User-confirm download on Windows; re-run benchmark with llama.cpp; EXE smoke with Günther on |
| 20 | Docs | Phase 0–2, benchmark, hardware, privacy, packaging, capabilities, hostile, this report |

## Model pin status (2026-09-15)

| ID | URL pinned | SHA256 | Notes |
|----|:----------:|:------:|-------|
| `qwen3-1.7b` LIGHT | **YES** | `72c5c3cb…250b24fb` | bartowski Q4_K_M; base Qwen Apache-2.0 |
| `qwen3-4b` STANDARD | **YES** | `7485fe6f…8534fdf5` | official `Qwen/Qwen3-4B-GGUF` Q4_K_M |
| `phi4-mini` | **NO** | — | **REVIEW REQUIRED** deferral — MIT OK, GGUF source not pinned yet |

Catalog: `guenther/model_manager.py` `MODEL_CATALOG`. Download still requires explicit `allow_download=True` (no silent fetch).

## Definition of Done

| DoD | Result |
|-----|--------|
| Architecture audit before implementation | **PASS** |
| Lifecycle not reimplemented | **PASS** |
| Local-first / offline after install | **PASS** |
| Structured validated outputs | **PASS** |
| UX German „Günther die Krake“ On/Off + Auto | **PASS** |
| Model manager non-silent | **PASS** |
| LIGHT (+STANDARD) URL+SHA256 pinned | **PASS** |
| Hostile + unit tests fictional | **PASS** |
| Privacy scan | **PASS** (re-verify after each push) |
| CI + Windows Smoke | **pending** on PR #19 |
| MERGE READY | **NO** until CI + Windows Smoke green |

## GÜNTHER STATUS

```
Base main:  8c1e81c9653789251e2500b249a9abbf3d7d3175
Branch:     cursor/guenther-local-ai-megapass-d85b
PR:         https://github.com/deadfrogface/Karrierekrake/pull/19
Runtime:    LocalAIProvider (llama_cpp | ollama-dev | heuristic | null)
Winning:    qwen3-4b (STANDARD Autopick) / Light: qwen3-1.7b (URL+SHA pinned)
Model pin:  LIGHT+STANDARD pinned; phi4-mini deferred REVIEW REQUIRED
CV/Job/Evidence/Email/Association/Writing/Interview: IMPLEMENTED (advisory)
Offline:    YES after model install | Cloud required: NO
Fallback:   fail-closed + optional heuristic | Prompt injection: separated layers
Safety:     Karrierekrake decides | Privacy: no PII logs | Licenses: MIT/Apache catalog
Tests:      guenther suite | CI/Windows Smoke: see PR checks
Remaining:  Windows live GGUF inference + EXE smoke with Günther on
MERGE READY: NO — await CI + Windows Smoke green
```
