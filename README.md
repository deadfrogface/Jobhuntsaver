# Jobhuntsaver

Lokale Windows-Desktop-App für Jobsuche und Bewerbungen in **Deutschland**.  
Kein Cloud-Konto, keine Pflicht-KI-API, keine Docker-Installation.

## Installation

1. Doppelklick auf **`setup.bat`**
2. Warten, bis „Setup erfolgreich!“ erscheint
3. Fertig

`setup.bat` prüft Python 3.11+, legt `.venv` an, installiert Runtime-Abhängigkeiten und Playwright Chromium und führt Basistests aus.

## Start

- **Desktop-App (Entwicklung):** Doppelklick auf **`start.bat`** (oder `start_desktop.bat`)
- **Fertige EXE:** `dist\Jobhuntsaver.exe` (bauen mit **`build.bat`**)
- **Nur Suche (CLI):** **`run_search.bat`**

Profil, Lebenslauf und Einstellungen liegen unter **`%LOCALAPPDATA%\Jobhuntsaver`**. YAML muss für den Normalbetrieb nicht manuell editiert werden.

## Profil einrichten

In der Desktop-App:

1. Seite **Profil** — Berufswünsche, Qualifikationen, Bewerbungsdaten, CV-Import  
2. Seite **Einstellungen** — Modus, Dry Run, Quellen, Automatik  

Optional (Legacy/CLI, Repo-`config\`):

- `config/profile.yaml` — Suchpräferenzen  
- `config/application_profile.yaml` — Bewerberdaten  
- Lebenslauf unter `%LOCALAPPDATA%\Jobhuntsaver\cvs\` (über die App speichern)

## Einstellungen (GUI oder YAML)

| Einstellung | Bedeutung |
|-------------|-----------|
| `mode: search_only` | Nur suchen, bewerten, anzeigen |
| `mode: review_before_submit` | Formulare ausfüllen, **nicht** absenden |
| `mode: fully_automatic` | Automatisch absenden (nur wenn sicher) |
| `dry_run: true` | Stoppt immer vor dem Absenden (empfohlen am Anfang) |
| `minimum_match_for_auto_apply: 75` | Ab welchem Score AutoApply erlaubt ist |

## Typischer Ablauf

1. Button „Suche starten“ in der GUI (oder `run_search.bat`)  
2. Jobs von Bundesagentur / Indeed (weitere Quellen optional)  
3. Filter: Distanz, Duplikate, Ausschlüsse  
4. Lokales Matching 0–100 mit Begründung  
5. In der GUI prüfen, Status setzen, AutoApply nur bei Dry Run / Review  

## Windows-Aufgabenplanung

Optional täglich um 08:00:

1. `scripts\setup_task_scheduler.bat` als Benutzer ausführen  
2. Oder XML importieren: `scripts\jobhuntsaver_task.xml` (Pfad anpassen)

Der Lauf startet, verarbeitet Jobs und **beendet sich danach**.

## Sicherheit & Privatsphäre

- Daten bleiben auf Ihrem PC (SQLite + AppData-YAML)
- Keine Telemetrie
- `.env`, CV, Cookies, Browser-Profil und Datenbank sind in `.gitignore`
- Niemals Passwörter oder Lebensläufe committen
- Profil-Reset in der App leert Bewerberdaten und CV-Speicher

## Lizenzen

Jobhuntsaver steht unter **GPL-3.0**.  
Wiederverwendete Teile stammen aus JobRadar (GPL-3.0) und AutoApply (MIT). Details: `NOTICE`, `docs/source-analysis.md`.

## Entwickler / Tests

```bat
call .venv\Scripts\activate.bat
pip install -r requirements-dev.txt
set PYTHONPATH=%cd%
pytest -q
python -m desktop.app
```

Weitere Doku: `docs/v1-optimization-report.md`, `docs/desktop-conversion.md`.
