"""Calendar availability + meeting collision helpers.

Collision logic adapted from PBP termin_dubletten ideas (MIT).
Google FreeBusy is optional; never exposes private event titles to employers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class CollisionResult:
    conflicts: tuple[str, ...]
    outside_working_hours: bool
    ok: bool


def _parse(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def parse_working_hours(spec: str) -> tuple[time, time]:
    """Parse '09:00-17:00' style config. Defaults Mon–Sun ignored here (time only)."""
    raw = (spec or "09:00-17:00").strip()
    try:
        left, _, right = raw.partition("-")
        sh, sm = left.strip().split(":")[:2]
        eh, em = right.strip().split(":")[:2]
        return time(int(sh), int(sm)), time(int(eh), int(em))
    except Exception:
        return time(9, 0), time(17, 0)


def overlaps(a: TimeWindow, b: TimeWindow) -> bool:
    return a.start < b.end and b.start < a.end


def check_interview_slot(
    proposed_start: str,
    *,
    duration_minutes: int = 60,
    busy: Iterable[TimeWindow] = (),
    working_hours: str = "09:00-17:00",
    existing_meetings: Iterable[dict[str, Any]] = (),
) -> CollisionResult:
    start = _parse(proposed_start)
    if not start:
        return CollisionResult(("invalid_datetime",), False, False)
    end = start.timestamp() + duration_minutes * 60
    end_dt = datetime.fromtimestamp(end, tz=start.tzinfo)
    window = TimeWindow(start, end_dt)

    wh_start, wh_end = parse_working_hours(working_hours)
    local_t = start.astimezone(timezone.utc).time() if start.tzinfo else start.time()
    # Compare clock time in the proposed timezone.
    local_t = start.timetz().replace(tzinfo=None)
    outside = not (wh_start <= local_t <= wh_end)

    conflicts: list[str] = []
    for b in busy:
        if overlaps(window, b):
            # Do not include private titles — only generic busy marker.
            conflicts.append("calendar_busy")
    for m in existing_meetings:
        other_start = _parse(str(m.get("scheduled_at") or m.get("start") or ""))
        if not other_start:
            continue
        other_end_raw = m.get("end")
        if other_end_raw:
            other_end = _parse(str(other_end_raw)) or other_start
        else:
            other_end = datetime.fromtimestamp(
                other_start.timestamp() + duration_minutes * 60, tz=other_start.tzinfo
            )
        if overlaps(window, TimeWindow(other_start, other_end)):
            conflicts.append(f"meeting_collision:{m.get('id') or 'existing'}")

    ok = not conflicts and not outside
    return CollisionResult(tuple(conflicts), outside, ok)


def availability_reply_slots(
    *,
    working_hours: str,
    busy: Iterable[TimeWindow],
    day_iso_dates: list[str],
    slot_minutes: int = 60,
) -> list[str]:
    """Return generic availability strings (no private event titles)."""
    wh_start, wh_end = parse_working_hours(working_hours)
    suggestions: list[str] = []
    busy_list = list(busy)
    for day in day_iso_dates:
        try:
            base = datetime.fromisoformat(f"{day}T{wh_start.strftime('%H:%M')}:00+00:00")
        except ValueError:
            continue
        cursor = base
        day_end = datetime.fromisoformat(f"{day}T{wh_end.strftime('%H:%M')}:00+00:00")
        while cursor.timestamp() + slot_minutes * 60 <= day_end.timestamp():
            end = datetime.fromtimestamp(cursor.timestamp() + slot_minutes * 60, tz=timezone.utc)
            win = TimeWindow(cursor, end)
            if not any(overlaps(win, b) for b in busy_list):
                suggestions.append(
                    f"{day} {cursor.strftime('%H:%M')}–{end.strftime('%H:%M')} UTC (verfügbar)"
                )
            cursor = end
            if len(suggestions) >= 6:
                return suggestions
    return suggestions
