"""Canonical salary normalization to EUR GROSS / YEAR.

Ambiguous or unknown salaries return ``(None, reason)`` so matchers can
score soft penalties without rejecting the job.
"""

from __future__ import annotations

import re
from typing import Any

# Documented assumption for hourly → annual conversion.
HOURS_PER_YEAR = 2080  # 40h/week * 52 weeks = 2080 hours/year

_ANNUAL_UNITS = frozenset(
    {"annual", "year", "yearly", "jahr", "jährlich", "jaehrlich", "p.a.", "pa"}
)
_MONTHLY_UNITS = frozenset(
    {"monthly", "month", "monat", "monatlich", "p.m.", "pm"}
)
_HOURLY_UNITS = frozenset(
    {"hourly", "hour", "stunde", "stunden", "pro stunde", "/h", "h"}
)

_UNKNOWN_PHRASES = (
    "nach vereinbarung",
    "verhandelbar",
    "competitive",
    "negotiable",
    "auf anfrage",
    "tbd",
    "n/a",
    "k.a.",
    "keine angabe",
)


def _norm_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    u = unit.strip().lower().replace("ä", "ae").replace("ü", "ue").replace("ö", "oe")
    u = u.replace(".", "").replace(" ", "")
    # Restore common keys after stripping
    aliases = {
        "jaehrlich": "jährlich",
        "jahr": "jahr",
        "yearly": "yearly",
        "annual": "annual",
        "year": "year",
        "monthly": "monthly",
        "month": "month",
        "monat": "monat",
        "monatlich": "monatlich",
        "hourly": "hourly",
        "hour": "hour",
        "stunde": "stunde",
        "stunden": "stunde",
        "prostunde": "stunde",
        "pa": "annual",
        "pm": "monthly",
        "/h": "hour",
        "h": "hour",
    }
    raw = unit.strip().lower()
    if raw in _ANNUAL_UNITS or aliases.get(u) in _ANNUAL_UNITS or u in {
        "annual",
        "year",
        "yearly",
        "jahr",
        "jaehrlich",
        "jährlich",
        "pa",
    }:
        return "annual"
    if raw in _MONTHLY_UNITS or aliases.get(u) in _MONTHLY_UNITS or u in {
        "monthly",
        "month",
        "monat",
        "monatlich",
        "pm",
    }:
        return "monthly"
    if raw in _HOURLY_UNITS or aliases.get(u) in _HOURLY_UNITS or u in {
        "hourly",
        "hour",
        "stunde",
        "stunden",
        "prostunde",
        "h",
    }:
        return "hourly"
    return None


def _parse_number(token: str) -> float | None:
    t = token.strip().lower().replace("€", "").replace("eur", "").replace(" ", "")
    if not t:
        return None
    # German thousands: 36.000 or 36.000,50 / English: 36,000.50
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", t):
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", t):
        t = t.replace(",", "")
    elif "," in t and "." not in t:
        # 36,5 → 36.5 or 36000,00
        parts = t.split(",")
        if len(parts[-1]) == 2 and parts[0].isdigit():
            t = parts[0] + "." + parts[1]
        else:
            t = t.replace(",", ".")
    mult = 1.0
    if t.endswith("k"):
        mult = 1000.0
        t = t[:-1]
    try:
        return float(t) * mult
    except ValueError:
        return None


def _detect_unit_in_text(text: str) -> str | None:
    low = text.lower()
    if re.search(
        r"\b(pro\s+jahr|per\s+year|/year|/jahr|jährlich|jaehrlich|annual|yearly|p\.?\s*a\.?)\b",
        low,
    ):
        return "annual"
    if re.search(
        r"\b(pro\s+monat|per\s+month|/month|/monat|monatlich|monthly|p\.?\s*m\.?)\b",
        low,
    ):
        return "monthly"
    if re.search(
        r"\b(pro\s+stunde|per\s+hour|/hour|/h\b|stündlich|stuendlich|hourly)\b",
        low,
    ):
        return "hourly"
    if "monat" in low:
        return "monthly"
    if "stunde" in low or "/h" in low:
        return "hourly"
    if "jahr" in low or "year" in low or "annual" in low:
        return "annual"
    return None


def _extract_from_text(text: str) -> tuple[float | None, str | None, str]:
    cleaned = text.strip()
    if not cleaned:
        return None, None, "empty salary text"
    low = cleaned.lower()
    if any(p in low for p in _UNKNOWN_PHRASES):
        return None, None, "salary unknown / negotiable"
    if not re.search(r"\d", cleaned):
        return None, None, "no numeric salary"
    unit = _detect_unit_in_text(cleaned)
    # Range like 30.000 – 40.000 or 30k-45k → ambiguous (do not hard-reject)
    if re.search(
        r"([\d.,]+)\s*k?\s*[-–—]\s*([\d.,]+)\s*k?",
        cleaned,
        re.I,
    ) or re.search(
        r"([\d.,]+)\s*k?\s*(?:bis|to)\s*([\d.,]+)\s*k?",
        cleaned,
        re.I,
    ):
        return None, unit, "ambiguous salary range"
    num_m = re.search(
        r"([\d.,]+)\s*(k)?\s*(?:€|eur|euro)?",
        cleaned,
        re.I,
    )
    if not num_m:
        return None, unit, "could not parse salary number"
    raw = num_m.group(1) + ("k" if num_m.group(2) else "")
    value = _parse_number(raw)
    if value is None:
        return None, unit, "invalid salary number"
    return value, unit, "ok"


def _to_annual(value: float, unit: str | None) -> tuple[int | None, str]:
    if unit == "annual":
        return int(round(value)), "annual"
    if unit == "monthly":
        return int(round(value * 12)), "monthly→annual"
    if unit == "hourly":
        return int(round(value * HOURS_PER_YEAR)), "hourly→annual (40h×52w=2080)"
    # Heuristic when unit missing: small numbers likely monthly/hourly
    if value < 100:
        return int(round(value * HOURS_PER_YEAR)), "assumed hourly→annual"
    if value < 10_000:
        return int(round(value * 12)), "assumed monthly→annual"
    return int(round(value)), "assumed annual"


def normalize_to_annual_gross_eur(
    value: Any = None,
    unit: str | None = None,
    text: str | None = None,
) -> tuple[int | None, str]:
    """Normalize a salary to EUR gross per year.

    Returns ``(annual_amount, reason)``. When the salary cannot be determined
    reliably, ``annual_amount`` is ``None`` and ``reason`` explains why — callers
    must not treat that as a hard job rejection.
    """
    explicit_unit = _norm_unit(unit)

    if text:
        parsed_val, text_unit, status = _extract_from_text(text)
        if parsed_val is None:
            # Fall through to numeric value if provided
            if value is None or value == "":
                return None, status
        else:
            use_unit = explicit_unit or text_unit
            if use_unit is None and status == "ambiguous salary range":
                return None, status
            if use_unit is None:
                annual, how = _to_annual(parsed_val, None)
                return annual, how
            annual, how = _to_annual(parsed_val, use_unit)
            return annual, how

    if value is None or value == "":
        return None, "salary not listed"

    if isinstance(value, str):
        return normalize_to_annual_gross_eur(None, unit=explicit_unit, text=value)

    try:
        num = float(value)
    except (TypeError, ValueError):
        return None, "invalid salary value"

    if num <= 0:
        return None, "non-positive salary"

    use_unit = explicit_unit
    annual, how = _to_annual(num, use_unit)
    return annual, how


def meets_minimum(
    job_annual: int | float | None,
    minimum_annual: int | float | None,
) -> bool | None:
    """Return True/False when both sides known; None if either is unknown."""
    if job_annual is None or minimum_annual is None:
        return None
    try:
        return int(job_annual) >= int(minimum_annual)
    except (TypeError, ValueError):
        return None


def job_annual_salary(job: Any) -> tuple[int | None, str]:
    """Resolve a Job's compensation to EUR gross / year using salary_min + salary_text."""
    salary_min = getattr(job, "salary_min", None)
    salary_text = getattr(job, "salary_text", None) or None
    return normalize_to_annual_gross_eur(
        salary_min if salary_min is not None else None,
        unit=None,
        text=salary_text,
    )
