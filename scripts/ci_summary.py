#!/usr/bin/env python3
"""Write a short GitHub Actions step summary from env/args.

Usage examples:
  python scripts/ci_summary.py --title "Tests" --status pass --body "All green"
  python scripts/ci_summary.py  # reads GITHUB_STEP_SUMMARY / CI_* env vars
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def build_markdown(
    *,
    title: str,
    status: str,
    body: str = "",
    extra_lines: list[str] | None = None,
) -> str:
    status_l = (status or "unknown").strip().lower()
    badge = {
        "pass": "✅ pass",
        "passed": "✅ pass",
        "ok": "✅ pass",
        "fail": "❌ fail",
        "failed": "❌ fail",
        "error": "❌ fail",
        "skip": "⏭️ skip",
        "skipped": "⏭️ skip",
    }.get(status_l, f"• {status}")
    lines = [
        f"## {title}",
        "",
        f"**Status:** {badge}",
        "",
    ]
    if body:
        lines.append(body.rstrip())
        lines.append("")
    for line in extra_lines or []:
        lines.append(line)
    if not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append markdown to GITHUB_STEP_SUMMARY")
    parser.add_argument("--title", default=os.environ.get("CI_SUMMARY_TITLE", "CI"))
    parser.add_argument("--status", default=os.environ.get("CI_SUMMARY_STATUS", "unknown"))
    parser.add_argument("--body", default=os.environ.get("CI_SUMMARY_BODY", ""))
    parser.add_argument(
        "--output",
        default=os.environ.get("GITHUB_STEP_SUMMARY") or "",
        help="Summary file path (defaults to GITHUB_STEP_SUMMARY)",
    )
    parser.add_argument(
        "--print",
        dest="do_print",
        action="store_true",
        help="Also print markdown to stdout",
    )
    args = parser.parse_args(argv)

    md = build_markdown(title=args.title, status=args.status, body=args.body)
    if args.do_print or not args.output:
        print(md, end="")
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
