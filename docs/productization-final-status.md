# Karrierekrake branding / UI / media — final status (agent)

## Baseline
- Base `origin/main`: newest after PR #12 (Stellenanker productization)
- Branch: `cursor/karrierekrake-branding-562a` (fresh from main)
- Display brand: **Karrierekrake** · Tagline: **FINDE. BEWIRB. BEHALTE DEN ÜBERBLICK.**
- Technical identity unchanged: Jobhuntsaver (AppData, EXE, scheduler, UA)

## Locked masters (not redrawn)
- MASTER A: `assets/brand/karrierekrake-logo-master.png`
- MASTER B: `assets/brand/karrierekrake-app-icon-master.png`
- Derivatives: `scripts/generate_brand_assets.py` → icons 1024→16, `app.ico`, `logo.png`, `social-preview.png`

## Palette
- Navy `#132238` · Teal `#18A999` · Orange `#E86A45` (brand art only)
- Success / warn / error + light/dark tokens in `desktop/branding.py` → `desktop/theme.py`

## UX
- About dialog (Einstellungen → Über Karrierekrake…) with MASTER A
- Wizard banner uses MASTER A; window/tray/sidebar use MASTER B sizes
- All user-facing Stellenanker / old anchor assets removed

## Media / docs
- Screenshots: `docs/assets/screenshots/01–06` (+ `07-about.png`)
- Demo: `docs/assets/demo/karrierekrake-demo.mp4` (~45s H.264)
- README landing rewritten for Karrierekrake
- `docs/name-research.md`, `docs/release-notes-template.md` updated

## CI / PR
- Branch pushed: `cursor/karrierekrake-branding-562a` @ `1f93f8466c411aca74d28fdf23a7a3b1c36d58ee`
- `gh pr create` / REST → **403** (integration cannot create PRs)
- ManagePullRequest tool **not available** in this agent tool catalog
- Compare URL: https://github.com/deadfrogface/Jobhuntsaver/compare/main...cursor/karrierekrake-branding-562a?expand=1
- CI + Windows Smoke blocked until a human/parent opens the PR
