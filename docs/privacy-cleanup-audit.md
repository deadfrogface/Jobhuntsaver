# Privacy cleanup — redacted audit report
#
# Sensitive literal values are intentionally omitted. See local backup / rewrite
# notes if operators need the full replacement map (never re-commit it).

## Summary

Real personal CV-derived content was present in the public GitHub repository
`deadfrogface/Jobhuntsaver`, primarily as test fixtures and comments introduced
when CV parsing was expanded. This cleanup removes that content from the
**current tree** and from **reachable Git history** via `git filter-repo`
(`--replace-text`), then force-pushes rewritten `main`.

## What was found (redacted)

| Category | Where | Commits (pre-rewrite SHAs, now obsolete) |
|----------|--------|------------------------------------------|
| Employer / workplace names from a personal CV | `tests/test_cv_parser.py`, `tests/test_matcher.py`, comments in `core/cv_parser.py` | Introduced in `ca5604d` (“Fix CV profile import…”); present through later tips until rewrite |
| Education / school / certificate strings from that CV | `tests/test_cv_parser.py` | Same lineage |
| Language combination unique to that CV | `tests/test_cv_parser.py`, parser comment | Same lineage |
| Local Windows user path to a CV PDF on Desktop | `tests/test_cv_parser.py` (`test_real_test_cv_if_present`) | Same lineage |
| Software / internal tool names tied to that CV | `tests/test_cv_parser.py`, parser comments | Same lineage |

Not treated as personal CV leaks (kept or replaced only where needed):

- Fictional `example.com` addresses and placeholder names (Mustermann / Alpha / Beta / Winterfeld)
- Generic product names used as matcher tokens when not part of the leaked CV narrative
- Empty example YAML personal fields

## Commit author email

All commits used a real Gmail address as author (`…@gmail.com`).

**Not rewritten** in this cleanup (would change every commit hash and is a separate
identity decision).

**Recommendation for the owner:** set future commits to the GitHub noreply address:

```text
git config user.email "<id>+<username>@users.noreply.github.com"
```

Optional later step: rewrite author emails with `git filter-repo --email-callback`
if hiding historical identity is required.

## Current-tree remediation

- Replaced structured CV tests with fully fictional persona **Lena Winterfeld**
  and companies **Nordhafen Logistik GmbH** / **Seeland Versand KG**.
- Removed Desktop PDF path test; fixtures live only under `tests/fixtures/`.
- Updated replace/merge fixtures `cv_a.txt` / `cv_b.txt` (fictional Alpha/Beta).
- Softened parser comments that echoed the leaked CV wording.
- Strengthened `.gitignore` for private configs, PDFs (with fixture exceptions),
  runtime state.
- Added `scripts/privacy_scan.py` + CI workflow job to block reintroduction of
  known fingerprints and Windows user paths.

## History rewrite method

1. Local backup bundle created **outside** the public repo (not pushed).
2. Clean tip committed with fictional tests and privacy tooling.
3. `git filter-repo --replace-text <local-replacements-file> --force`
   applied to rewrite **all** blobs so leaked tokens no longer appear in
   historical file versions.
4. Remotes re-added; `git push --force --all` and `git push --force --tags`.
5. Post-push verification: `git grep` / `git log -S` for fingerprints; GitHub
   old SHA URLs should 404 / be unreachable from refs.

## Branches / tags

Pre-cleanup: only `main` (local + `origin/main`). No other branches or tags.

## GitHub cache note

Even after a successful force-push, GitHub may temporarily retain unreachable
objects. Direct checks of pre-rewrite commit SHAs still returned HTTP 200 from
`github.com/.../commit/<old-sha>` immediately after the rewrite, while
`git ls-remote` showed only the new `main` tip and retargeted tag `Vers.1.0`.

**Action for the repository owner:** open a GitHub Support ticket requesting
removal of cached/unreachable sensitive blobs for `deadfrogface/Jobhuntsaver`,
and re-check code search + old commit URLs after their purge.

Do not rely only on the new branch tip. If a direct object URL still serves
sensitive content after refs are clean, Support must purge caches.

## Verification checklist

- [x] No real CV fingerprints in current tracked files (`scripts/privacy_scan.py`)
- [x] No `Users\\…` developer paths in tests (history rewritten to `tests/fixtures/…`)
- [x] Example configs remain empty of personal data
- [x] pytest passes with fictional fixtures
- [x] History rewrite (`git filter-repo` replace-text + blob-callback) + force-push performed
- [ ] Owner confirms old commit URLs / GitHub code search are clean
