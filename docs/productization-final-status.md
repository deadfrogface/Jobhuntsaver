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

## Verification
- Pytest: **299 passed**
- Privacy scan: **PASS**
- Offscreen smoke: **SMOKE_TEST_OK**
- Tiny icons 16/24/32 inspected (legible octopus silhouette)
- Screenshots + About + demo regenerated from real app + fictional data
