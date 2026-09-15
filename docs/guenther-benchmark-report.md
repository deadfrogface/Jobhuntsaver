# Günther — Benchmark Report (updated with live GGUF)

**Corpus:** `benchmark/corpus/guenther_de_fictional.json`  
**CI baseline:** `benchmark/results.json` (heuristic)  
**Live GGUF:** `benchmark/results_live_gguf.json` / `results_live_summary.json`

## Live run (llama-cpp-python, CPU)

| Model | Safety penalty | Meets threshold | Utility | Wall (approx) |
|-------|---------------:|:---------------:|--------:|--------------|
| **qwen3-1.7b** | 0 | **YES** | ~71.6 | ~3 min |
| qwen3-4b | 40 (injection_follow) | **NO** | ~31.6 | ~5 min |

**Live winner (smallest meeting safety):** `qwen3-1.7b`  
Product Autopick: LIGHT=`qwen3-1.7b` (also live winner). STANDARD catalog remains `qwen3-4b` for optional higher-RAM installs, but live safety failed injection trap — deterministic classify/associate gates stay authoritative for consequential actions.

## Notes from live debugging

- Qwen3 emits `<think>` — stripped + `/no_think` in provider/prompts.
- String `anchors_used` coerced to ClaimAnchor.
- Interview scorer previously false-positived when any DIRECT item coexisted with a forbidden claim string; fixed to per-item checks.
