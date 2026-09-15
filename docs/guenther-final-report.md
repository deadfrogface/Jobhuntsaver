# Günther die Krake — Final Report

**Feature branch:** `cursor/guenther-local-ai-megapass-d85b`  
**PR:** https://github.com/deadfrogface/Karrierekrake/pull/19  
**Base `origin/main`:** `8c1e81c9653789251e2500b249a9abbf3d7d3175`  
**Verified green head (CI + Windows Smoke):** `95cbec961d96192a95bcf990d895074671b558d6`  
**Lifecycle gate:** PR #17 + #18 present on main — proceeded (not blocked).  
**PR title:** `feat(ai): Günther local intelligence — offline CV, job, mail & interview AI`  
**Do not merge** without human review — agent must not merge.

## CI / Windows Smoke @ `95cbec9`

| Check | Workflow | Result | Run |
|-------|----------|--------|-----|
| unit-tests | CI | **PASS** | `34964330079` |
| privacy | CI | **PASS** | `34964330079` |
| cv-regression | CI | **PASS** | `34964330079` |
| database-migration-tests | CI | **PASS** | `34964330079` |
| static-smoke | CI | **PASS** | `34964330079` |
| qt-smoke | Windows Smoke | **PASS** | `34964330137` |
| build-and-exe-smoke | Windows Smoke | **PASS** | `34964330137` |

**Suite rollup:** CI **PASS** · Windows Smoke **PASS** (7/7).

## Mission checklist (20 items)

| # | Item | Status |
|---|------|--------|
| 1 | Base SHA | `8c1e81c9653789251e2500b249a9abbf3d7d3175` |
| 2 | Head SHA (verified green) | `95cbec961d96192a95bcf990d895074671b558d6` |
| 3 | Runtime | Abstract `LocalAIProvider`; primary WRAP `llama-cpp-python` (optional); Ollama optional dev; heuristic/null fail-closed |
| 4 | Models catalog | Qwen3 1.7B + 4B URL+SHA256 pinned; Phi-4-mini deferred REVIEW REQUIRED — **no weights in git** |
| 5 | Winner | Product Autopick STANDARD=`qwen3-4b`, LIGHT=`qwen3-1.7b`; CI baseline=`heuristic-local` |
| 6 | Sizes | LIGHT ~1.28 GB; STANDARD ~2.50 GB (Q4_K_M) |
| 7 | RAM | LIGHT ≥~3 GB; STANDARD ≥~5 GB |
| 8 | Licenses | Runtime MIT; Qwen Apache-2.0; Phi MIT (deferred); Gemma 3 rejected as default |
| 9 | Reuse | WRAP llama.cpp/python; EXISTING Pydantic, matcher, classify/associate, lifecycle |
| 10 | Original | provider abstraction, validation, model manager, prompts, service, benchmark |
| 11 | Capabilities | CV/Job/Evidence/Email/Association/Writing/Interview — advisory |
| 12 | Fallbacks | disabled / not installed / missing model / invalid / timeout / OOM / cancel |
| 13 | Safety | No submit/send/finalize/CAPTCHA; no silent HIGH assoc; false-reject guard; claim guards |
| 14 | Tests | `tests/test_guenther_local_ai.py` + CI unit-tests PASS |
| 15 | Privacy | No cloud fallback; no PII keys in logs; AppData models; privacy job PASS |
| 16 | Windows Smoke | **PASS** (qt-smoke + build-and-exe-smoke) |
| 17 | EXE | Spec collects `guenther`; weights not bundled; EXE smoke PASS |
| 18 | Limitations | Live GGUF inference not run in CI; Phi download deferred REVIEW REQUIRED |
| 19 | Remaining live tests | User-confirm model download on Windows laptop; re-run benchmark with llama.cpp loaded |
| 20 | Docs | Phase 0–2, benchmark, hardware, privacy, packaging, capabilities, hostile, this report |

## Model pin status

| ID | URL pinned | SHA256 | Notes |
|----|:----------:|:------:|-------|
| `qwen3-1.7b` LIGHT | **YES** | `72c5c3cb…250b24fb` | bartowski Q4_K_M; base Qwen Apache-2.0 |
| `qwen3-4b` STANDARD | **YES** | `7485fe6f…8534fdf5` | official `Qwen/Qwen3-4B-GGUF` Q4_K_M |
| `phi4-mini` | **NO** | — | **REVIEW REQUIRED** deferral (does not block MERGE READY) |

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
| Privacy scan / CI privacy | **PASS** |
| CI + Windows Smoke | **PASS** @ `95cbec9` |
| MERGE READY | **YES** (for green SHA `95cbec9`; human merge only; do not auto-merge) |

## GÜNTHER STATUS

```
Base main:  8c1e81c9653789251e2500b249a9abbf3d7d3175
Branch:     cursor/guenther-local-ai-megapass-d85b
PR:         https://github.com/deadfrogface/Karrierekrake/pull/19
Green SHA:  95cbec961d96192a95bcf990d895074671b558d6
Runtime:    LocalAIProvider (llama_cpp | ollama-dev | heuristic | null)
Winning:    qwen3-4b (STANDARD) / Light: qwen3-1.7b (URL+SHA pinned)
Model pin:  LIGHT+STANDARD pinned; phi4-mini deferred (non-blocking)
CV/Job/Evidence/Email/Association/Writing/Interview: IMPLEMENTED (advisory)
Offline: YES | Cloud required: NO | Fallback: fail-closed | Injection: layered
Safety: Karrierekrake decides | Privacy: no PII logs | Licenses: MIT/Apache
CI: PASS (5) | Windows Smoke: PASS (qt-smoke + build-and-exe-smoke)
Remaining live: user download + local llama.cpp benchmark on Windows
MERGE READY: YES
```
