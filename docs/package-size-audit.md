# Package size audit

Measured under `.venv/Lib/site-packages` (Windows, development venv) on 2026-09-08.

Method: recursive directory size (`os.walk` / equivalent to `du`). Sorted descending.

## Top packages by size

| Size (MB) | Package / folder | Decision | Notes |
|-----------|------------------|----------|-------|
| 632.4 | PySide6 | **KEEP** | Desktop UI |
| 106.5 | playwright | **KEEP** | Browser automation (lazy import) |
| 78.1 | tls_client | **KEEP** | Required by python-jobspy on Windows |
| 64.2 | pandas | **KEEP** | jobspy scrape_jobs returns DataFrames |
| 31.3 + 20.2 | numpy (+ libs) | **KEEP** | pandas dependency |
| 15.5 | PIL / Pillow | **KEEP** | Indirect (pdf / image tooling) |
| 8.9 | lxml | **KEEP** | HTML parsing |
| 3.8 | pypdf | **KEEP** | CV PDF text |
| 3.0 | shiboken6 | **KEEP** | PySide6 binding |
| 2.3 | docx / python-docx | **KEEP** | CV DOCX |
| ~small | jobspy (python-jobspy) | **KEEP** | Indeed/LinkedIn search adapter |
| — | streamlit | **REMOVE** | UI deleted (`ui/app.py`); dropped from `requirements-dev.txt` |
| — | openpyxl | **REMOVE** | Not used by desktop runtime; do not re-add |

Site-packages total (this venv): **~1039 MB** (dominated by PySide6 + Playwright + tls_client + pandas/numpy).

## Packaging implications

- Runtime install should follow `requirements-runtime.txt` (no Streamlit).
- Chromium browser binaries live under `%LOCALAPPDATA%\Jobhuntsaver\browsers` — not counted in site-packages.
- Further size cuts would mean dropping Indeed/JobSpy (tls_client+pandas) or Qt widgets — out of scope for V1.

## KEEP / REMOVE summary

| KEEP | REMOVE |
|------|--------|
| PySide6, playwright, tls_client, pandas, numpy, python-jobspy, pdf/docx stack, PyYAML, requests/httpx as needed | streamlit, openpyxl (unused), any accidental Streamlit transitive UI stack |
