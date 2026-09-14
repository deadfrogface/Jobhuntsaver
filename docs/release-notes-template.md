# Release notes template

## Karrierekrake (Jobhuntsaver) — vX.Y.Z

**Date:** YYYY-MM-DD  
**Platform:** Windows 10/11 (x64)  
**Artifact:** `Jobhuntsaver.exe` (onefile)  
**Display brand:** Karrierekrake · Tagline: FINDE. BEWIRB. BEHALTE DEN ÜBERBLICK.

### Highlights

- …
- …

### Safety defaults (unchanged intent)

- Dry-run on by default for new setups
- CAPTCHA / 2FA / review stop before submit
- Unsupported ATS never auto-submitted
- Dedup + status preservation
- Local-only data under `%LOCALAPPDATA%\Jobhuntsaver`

### Install

1. Download `Jobhuntsaver.exe` from this release
2. Run it (Windows may show SmartScreen for unsigned builds — “More info” → Run anyway)
3. Complete the 3-step first-run wizard
4. Click **Jobs finden**

Optional: clone the repo and run `setup.bat` for a development install.

### Verify

- SHA256: `<paste from CI Windows Smoke log>`
- Approximate size: ~160 MB (Chromium downloaded separately on demand)
- EXE icon: multi-size `assets/brand/app.ico` (MASTER B octopus)

### Known limitations

- V1 sources focus on Bundesagentur + Indeed (others may be limited/placeholder)
- No cloud sync, no payments, no AI API required
- German job market focus

### Links

- Screenshots: `docs/assets/screenshots/`
- Demo: `docs/assets/demo/karrierekrake-demo.mp4`
- Brand assets: `assets/brand/`
