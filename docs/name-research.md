# Product name research — Karrierekrake (display brand)

Repo / technical identity remains **Jobhuntsaver**
(`%LOCALAPPDATA%\Jobhuntsaver`, `Jobhuntsaver.exe`, GitHub repo name unchanged).

## Decision

| # | Name | Notes |
|---|------|-------|
| 1 | **Karrierekrake** | Distinctive German compound (“career octopus”). Matches locked master artwork (octopus + glasses + laptop). Strong mnemonic for multi-task job search. **Winner.** |
| — | Stellenanker | Prior working title; **retired** from all user-facing surfaces. |
| — | Bewpfad / Stellweg / Bewmate | Earlier shortlist; not selected. |
| — | Joblotse | Rejected — collision with [joblotse.de](https://joblotse.de/). |

## Tagline

**FINDE. BEWIRB. BEHALTE DEN ÜBERBLICK.**

## Assets

- MASTER A (large): `assets/brand/karrierekrake-logo-master.png` — README, onboarding, About, social
- MASTER B (icon): `assets/brand/karrierekrake-app-icon-master.png` — EXE / tray / small UI
- Derivatives only via `scripts/generate_brand_assets.py` (Pillow resize — no redraw)

## Change surface

`desktop/branding.py` (`DISPLAY_NAME`, palette tokens, asset helpers).  
Do **not** rename the GitHub repository or wipe AppData without a tested migration.
