# Jobhuntsaver - Fictional CV Regression Corpus

This corpus contains 10 fully fictional CVs:
- 5 German
- 5 English
- single-column, two-column, compact and two-page layouts
- different section names and date formats
- deliberate parser traps
- missing-field cases

Important:
- No real user data is included.
- Do not train or hard-code the parser against these exact values.
- Treat each PDF as a black-box acceptance test.
- expected_results.json contains the expected structured outputs/counts.
- A parser fix is accepted only if it improves generalization across the corpus and does not regress previously passing fixtures.

Deliberate traps include:
- document titles such as "FIKTIVER TEST-LEBENSLAUF", "CURRICULUM VITAE" and "Resume" must never become a person's name
- CEFR levels C1/B1/A2 must not be treated as driving licences outside an explicit licence section
- one fixture contains a genuine C1 driving licence in an explicit licence section
- section headings must not become values
- missing contact fields must remain missing rather than being invented
- software/skills/certificates use varied section aliases
