# CV corpus acceptance — fictional DE/EN regression suite

## Result matrix (black-box vs `expected_results.json`)

Run: `python scripts/run_cv_corpus.py`

```
CV                                   pers     addr     lang     lice     educ     work     cert     soft     skil
---------------------------------------------------------------------------------------------------------------------
DE_01_Klassisch.pdf                  PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS
DE_02_Zweispaltig_Trap.pdf           PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS
DE_03_C1_Kontextfalle.pdf            PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS
DE_04_Unvollstaendige_Kontaktdaten.pdf PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS
DE_05_Zweiseitig.pdf                 PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS
EN_01_Classic_Resume.pdf             PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS
EN_02_Two_Column_Trap.pdf            PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS
EN_03_Missing_Address_Fields.pdf     PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS
EN_04_German_Address_English_CV.pdf  PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS
EN_05_Skills_Heavy.pdf               PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS     PASS

10/10 documents fully PASS
```

## Root causes addressed (generic)

1. **Document titles as names** — `Resume` / `CURRICULUM VITAE` / `FIKTIVER TEST-LEBENSLAUF` / `PROFILE` skipped before header/name extraction.
2. **CEFR vs driving licence** — no full-text licence scan; only licence section or explicit `Führerschein:` / `Klassen …` / `Category …` phrases. `C1` valid inside licence context (`DE_03`).
3. **Section aliases** — shared DE/EN heading map (`EMPLOYMENT HISTORY`, `TECH STACK`, `WEITERE KENNTNISSE`, `ACADEMIC BACKGROUND`, …). Bare `Kenntnisse` → skills; tool lists → software.
4. **Multi-line / pipe layouts** — date-first education & experience; `|`-separated title/company; English month/year ranges.
5. **Addresses** — DE PLZ, UK/IE postcodes; city-only headers without inventing street/phone/DoB.
6. **Import safety** — low-confidence personal/sections filtered before merge; missing fields do not invent values.

## Fixtures

- `tests/fixtures/cv_corpus/` — 10 fictional PDFs + `expected_results.json` + `README.txt`
- Automated: `tests/test_cv_corpus.py`, `tests/test_cv_parser_generic.py`
- Packaged smoke: `Jobhuntsaver.exe --smoke-cv-corpus <pdf>…`
