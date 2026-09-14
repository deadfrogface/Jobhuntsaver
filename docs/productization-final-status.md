# Karrierekrake — zero-legacy product rename status

## Baseline

- Base `origin/main`: `d300d27` (after adversarial abuse PR #14)
- Branch: `cursor/karrierekrake-final-rename-d85b`
- Product name (display + technical): **Karrierekrake**
- Tagline: **FINDE. BEWIRB. BEHALTE DEN ÜBERBLICK.**

## What changed

- Technical identity migrated from Jobhuntsaver → Karrierekrake (constants, loggers, env vars, UA, scheduler, single-instance keys)
- EXE / PyInstaller: `packaging/Karrierekrake.spec` → `Karrierekrake.exe`
- AppData canonical path: `%LOCALAPPDATA%\Karrierekrake`
- One-time safe migration from legacy AppData folder (isolated in `desktop/legacy_migration.py`)
- CI / Windows Smoke / build scripts / docs / README updated
- Regression: `tests/test_product_rename_migration.py` (zero-legacy scan + migration matrix)

## Migration rules

1. No data loss
2. Idempotent / restart-safe
3. Legacy folder left intact after successful copy
4. Only `desktop/legacy_migration.py` may mention the retired folder name

## Remaining human step

GitHub repository rename to `deadfrogface/Karrierekrake` requires admin rights (do last, after merge).
