# Agent / contributor branch hygiene

## Always start bug-hunt and release-fix PRs from latest `main`

```bash
git fetch origin
git checkout -B cursor/<short-topic>-d85b origin/main
```

## Do not reuse long-lived implementation branches after merge

Once a Cursor branch has been merged (or its work landed via another PR), **do not keep committing on it**.

Reusing branches such as `cursor/v1-noconsole-qthread-d85b` after their fixes are on `main` creates stale PRs that:

- replay already-merged history
- conflict with newer `main`
- hide genuine net-new fixes inside huge diffs

## Continuing unfinished work

1. `git fetch origin`
2. Compare `merge-base` of your branch with `origin/main`
3. If the branch tip is not a fast-forward of current `main`, create a **fresh** branch from `origin/main` and **port only net-new diffs** (do not merge the stale branch wholesale)

## Before opening a PR

Confirm:

- branch was created from the current `origin/main` SHA
- diff against `main` contains only intended net-new changes
- CI + Windows Smoke are expected to run on that SHA
