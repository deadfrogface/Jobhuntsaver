# Desktop Conversion Plan – Jobhuntsaver

## Phase 2 decision

### Chosen: **Option D – Build new PySide6 interface**

| Option | Verdict |
| ------ | ------- |
| A – Reuse AutoApply UI | Rejected: Flask/JS SPA tightly coupled; reuse needs API rewrite |
| B – Reuse JobRadar UI | Rejected: browser Alpine SPA, no settings/tray/exe, GPL-3.0 |
| C – Combine both | Rejected: combining two web stacks increases weight without Qt widgets |
| **D – New PySide6** | **Selected**: least total code + deps for a real `.exe` |

### Why this is maximum reuse

- **Backend:** keep `core/`, `search/`, `apply/`, `browser/`, `app.main.run_pipeline` unchanged where possible.
- **UX:** mirror AutoApply navigation (Dashboard / Applications / Settings / Wizard / Tray) and JobRadar job-list filters.
- **Do not** import Electron, Node, Flask UI, or Alpine SPA.

## Target architecture

```
Jobhuntsaver.exe
  └── desktop/ (PySide6)
        ├── ConfigService  → YAML in %LOCALAPPDATA%\Jobhuntsaver\config
        ├── Workers        → QThread calling run_pipeline
        ├── Pages          → Dashboard, Jobs, Applications, Profile, Settings, Logs
        ├── Wizard         → first run
        └── Tray           → minimize / Search Now / Pause / Exit
  └── existing backend modules
```

## App data location

`%LOCALAPPDATA%\Jobhuntsaver\`

- `config/` – profile, application_profile, settings YAML
- `data/jobs.db`
- `logs/`
- `browser_profile/`
- `cvs/`
- `cache/`
- `meta.json` – first-run flag, schedule metadata

## Implementation phases (this conversion)

1. Analysis docs (done)
2. Decision Option D (done)
3. ConfigService + AppData paths + save/validate
4. PySide6 main window + pages
5. Dry run / test mode controls
6. Tray + Windows schedule helper
7. First-run wizard
8. PyInstaller + `build.bat`
9. Smoke tests

## Acceptance mapping

| Criterion | Implementation |
| --------- | -------------- |
| Double-click EXE | PyInstaller one-folder `dist/Jobhuntsaver/Jobhuntsaver.exe` |
| First-run setup | Wizard; defaults: Search Only, Dry Run ON, Auto OFF |
| GUI settings | ConfigService read/write YAML |
| Search button | Worker → `run_pipeline(..., mode=search_only)` |
| Jobs / match | Jobs page ← `Database.list_jobs` |
| Applications / review | Applications page + review filter |
| Dry run | Settings toggle → `settings.dry_run` |
| Automatic runs | ScheduleService + GUI |
| Tray | QSystemTrayIcon |
| No YAML/terminal/Streamlit | Desktop is primary entry; Streamlit UI removed from the product |
