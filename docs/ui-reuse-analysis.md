# UI Reuse Analysis – AutoApply & JobRadar

**Date:** 2026-09-08  
**Goal:** Windows desktop app `Jobhuntsaver.exe` with maximum reuse, minimum new code.

## Source inspection

| Project | URL | UI stack | Desktop packaging |
| ------- | --- | -------- | ----------------- |
| AutoApply | https://github.com/AbhishekMandapmalvi/AutoApply | Flask + Vanilla JS SPA + Socket.IO in **PyWebView** (~8k LOC UI) | PyInstaller + pystray |
| JobRadar | https://github.com/jason-huanghao/jobradar | FastAPI + **Alpine.js** single HTML (~567 LOC) in browser | None (local web) |
| Jobhuntsaver (current) | this repo | **PySide6 desktop** (`desktop/`) | PyInstaller onefile EXE |

> **Update (2026-09-09):** Streamlit `ui/` was removed. This document records the pre-desktop analysis; the shipping UI is Qt Desktop.

## Comparison table

| UI Area | AutoApply | JobRadar | Reusable? | Modification Required |
| ------------------- | --------- | -------- | --------- | --------------------- |
| Dashboard | Full bot dashboard (start/pause, stats, feed, review card) | Stats + top matches | **UX ideas only** | Full rewrite for Jobhuntsaver API/DB |
| Job List | No dedicated job inbox (applications-centric) | Jobs page + client filters | **UX ideas only** | JobRadar filters map well, but Alpine≠Qt |
| Job Detail | Application detail modal | Slide-over panel + score breakdown | **UX ideas only** | Rebuild against `core.database` / `Job` |
| Applications | Strong table + status + timeline | Status on jobs only | **UX ideas only** | AutoApply shapes differ from our `applications` table |
| Profile | Experience files / KB-oriented | Read-only CV extract display | **No meaningful code reuse** | Need editable Jobhuntsaver YAML fields |
| Settings | Large settings screen (AI, schedule, login) | API only, **no settings UI** | **UX ideas only** | Must map to our YAML `ConfigService` |
| CV Selection | Resume library (heavy) | Upload → LLM extract | Partial idea | Simple local CV picker sufficient |
| Automation Controls | Start/Pause/Stop + apply modes | Pipeline run via WS | **UX ideas only** | Wire to `run_pipeline` / workers |
| Logs | Activity feed (Socket.IO) | Pipeline log panel | **UX ideas only** | Use our `logs/` / `RunLogger` |
| First-run Wizard | Yes (~7 steps) | No | Pattern only | Rebuild for Jobhuntsaver defaults |
| System Tray | `shell/tray.py` (pystray) | No | Pattern only | Prefer Qt tray with PySide6 |
| Browser / sessions | Playwright login UI | N/A | Pattern only | Keep `browser.BrowserManager` |

## Weight & coupling

### AutoApply
- Not Electron (removed); still a **web SPA** hosted by Flask inside PyWebView.
- Every JS module calls AutoApply `/api/*` and Socket.IO events.
- Reuse would require either forking AutoApply’s entire API or rewriting all fetch calls → **not less code** than a native UI.
- Extra stack: Flask, Flask-SocketIO, gevent, CDN Chart.js/Socket.IO.

### JobRadar
- Tiny SPA; **GPL-3.0** package license.
- No settings UI, no tray, no `.exe` path.
- Alpine/HTML cannot drop into PySide6; port ≈ rewrite.
- Hybrid WebView would pull FastAPI + GPL risk + different domain model.

## Preferred runtime (plan §6)

Python + **PySide6** + SQLite + Playwright — confirmed as lightest path that meets acceptance criteria without Node/Electron.

## Decision

See `docs/desktop-conversion.md` → **Option D: Build new PySide6 interface**.

Reuse is limited to:
- Screen map / UX patterns from AutoApply (dashboard controls, applications table, wizard, tray menu)
- Job list/filter UX from JobRadar
- Existing Jobhuntsaver backend (`core/`, `search/`, `apply/`, `browser/`, `app.main.run_pipeline`)
