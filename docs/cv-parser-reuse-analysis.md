# CV-Parser reuse analysis

## Goal

Decide whether Jobhuntsaver should vendor or depend on an external CV/resume parser, or keep the lightweight local heuristic parser (`core/cv_parser.py`).

## Candidates

| Project | License | Stack | Fit for DE desktop |
|---------|---------|-------|--------------------|
| **pyresume / leverparser-style** (MIT community parsers) | MIT | Regex / HTML form helpers | Ideas only — small patterns OK |
| **pyresparser** | GPL / heavy deps (spaCy, NLTK) | NLP models | Poor fit — large download, GPL coupling, English-centric |
| **open-resume** | AGPL / product UI | Next.js web app | Do **not** vendor — wrong runtime, license friction |
| **Jobhuntsaver `core/cv_parser.py`** | GPL-3.0 (this repo) | pdfplumber/docx + DE heuristics | Current choice |

## Findings

1. **Heavy NLP (spaCy / transformers)** balloons install size and startup time; offers little gain for German form fields we already extract with section headers and regex.
2. **open-resume** is a full web product — vendoring it would fight the PySide6 desktop architecture and add AGPL obligations beyond our existing GPL baseline without clear benefit.
3. **MIT parsers** (generic resume regex / Lever helpers) are useful as *idea sources* (field names, section titles, date patterns), not as drop-in packages.
4. German CVs need local normalization (Führerschein classes, “Berufserfahrung”, PLZ+Ort) which generic EN parsers miss.

## Conclusion

**Keep the lightweight local parser + German normalization.**

- Reuse optional *ideas* (section headings, date formats, skill list splitting) from MIT sources when useful.
- **No** heavy NLP dependency.
- **Do not** vendor entire apps (open-resume, full pyresparser pipelines).
- Continue improving `core/cv_parser.py` with fixtures (`tests/fixtures/cv_*.txt`) and replace/merge UX already in the desktop profile page.
