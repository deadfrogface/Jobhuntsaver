"""Safe live source-health probes for workflow_dispatch / schedule.

Never applies, never submits, never bypasses login/CAPTCHA.
"""

from __future__ import annotations

import traceback

from core.source_health import SourceHealthStatus
from search.registry import build_sources


def main() -> int:
    sources = build_sources(
        ["bundesagentur", "indeed", "linkedin", "stepstone", "xing", "company_sites"]
    )
    lines: list[str] = []
    for src in sources:
        placeholder = src.source_id == "company_sites"
        try:
            ok, msg = src.health_check()
            status = SourceHealthStatus.from_outcome(
                jobs_found=1 if ok and not placeholder else 0,
                error=None if ok else msg,
                source_id=src.source_id,
                placeholder=placeholder,
            )
            if placeholder:
                status = SourceHealthStatus.PLACEHOLDER
            elif ok and not placeholder:
                # health_check success ≠ results; mark as health-ok diagnostic only
                lines.append(f"{src.source_id}: HEALTH_OK ({msg}) [{status.value}]")
                continue
            lines.append(f"{src.source_id}: {status.value} ({msg})")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"{src.source_id}: ERROR ({exc})")
            lines.append(traceback.format_exc(limit=3))
    text = "\n".join(lines)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
