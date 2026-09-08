# Jobhuntsaver

Einfaches, lokales System für Jobsuche und Bewerbungen in **Deutschland**.  
Kein Cloud-Konto, keine Pflicht-KI-API, keine Docker-Installation.

## Installation

1. Doppelklick auf **`setup.bat`**
2. Warten, bis „Setup erfolgreich!“ erscheint
3. Fertig

`setup.bat` prüft Python, legt eine virtuelle Umgebung an, installiert Abhängigkeiten und Playwright, erstellt Ordner und Beispiel-Konfigurationen und initialisiert die Datenbank.

## Start

- **Oberfläche:** Doppelklick auf **`start.bat`**
- **Nur Suche:** Doppelklick auf **`run_search.bat`**

Die Oberfläche öffnet sich im Browser (lokal, typischerweise Port 3847).

## Profil einrichten

1. Öffnen Sie `config/profile.yaml`  
   - Wunsch-Jobtitel  
   - Home-Adresse und max. Pendelstrecke  
   - Max. Pendelstrecke (Standard: 20 km)  
   - Remote / Hybrid  
   - Skills, Sprachen, Ausschlussbegriffe
2. Öffnen Sie `config/application_profile.yaml`  
   - Name, E-Mail, Telefon, CV-Pfad  
   - Nur Antworten eintragen, die Sie **sicher** wissen
3. Legen Sie Ihren Lebenslauf unter `private/cv.pdf` ab (Ordner wird nicht ins Git committed)

## Einstellungen

In `config/settings.yaml`:

| Einstellung | Bedeutung |
|-------------|-----------|
| `mode: search_only` | Nur suchen, bewerten, anzeigen |
| `mode: review_before_submit` | Formulare ausfüllen, **nicht** absenden |
| `mode: fully_automatic` | Automatisch absenden (nur wenn sicher) |
| `dry_run: true` | Stoppt immer vor dem Absenden (empfohlen am Anfang) |
| `minimum_match_for_auto_apply: 75` | Ab welchem Score AutoApply erlaubt ist |

## Typischer Ablauf

1. `run_search.bat` oder Button „Suche starten“ in der GUI  
2. Jobs von Bundesagentur / Indeed (weitere Quellen optional)  
3. Filter: >20 km weg (außer echtes Remote in DE), Duplikate, Ausschlüsse  
4. Lokales Matching 0–100 mit Begründung  
5. In der GUI prüfen, Status setzen, exportieren  

## Windows-Aufgabenplanung

Optional täglich um 08:00:

1. `scripts\setup_task_scheduler.bat` als Benutzer ausführen  
2. Oder XML importieren: `scripts\jobhuntsaver_task.xml` (Pfad anpassen)

Der Lauf startet, verarbeitet Jobs und **beendet sich danach**.

## Sicherheit & Privatsphäre

- Daten bleiben auf Ihrem PC (SQLite)
- Keine Telemetrie
- `.env`, CV, Cookies, Browser-Profil und Datenbank sind in `.gitignore`
- Niemals Passwörter oder Lebensläufe committen

## Lizenzen

Jobhuntsaver steht unter **GPL-3.0**.  
Wiederverwendete Teile stammen aus JobRadar (GPL-3.0) und AutoApply (MIT). Details: `NOTICE`, `docs/source-analysis.md`.

## Entwickler / Tests

```bat
call .venv\Scripts\activate.bat
set PYTHONPATH=%cd%
pytest -q
python -m app.main --mode search_only
```
