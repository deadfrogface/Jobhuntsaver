"""ATS detection from application URLs.

Adapted and extended from AutoApply core/filter.py detect_ats (MIT).
"""

from __future__ import annotations

# Longer / more specific fingerprints first.
ATS_FINGERPRINTS: list[tuple[str, str]] = [
    ("boards.greenhouse.io", "greenhouse"),
    ("job-boards.greenhouse.io", "greenhouse"),
    ("greenhouse.io", "greenhouse"),
    ("jobs.lever.co", "lever"),
    ("lever.co", "lever"),
    ("myworkdayjobs.com", "workday"),
    ("wd1.myworkdaysite.com", "workday"),
    ("wd3.myworkdaysite.com", "workday"),
    ("workday.com", "workday"),
    ("ashbyhq.com", "ashby"),
    ("jobs.ashbyhq.com", "ashby"),
    ("linkedin.com/jobs", "linkedin"),
    ("linkedin.com", "linkedin"),
    ("de.indeed.com", "indeed"),
    ("indeed.com", "indeed"),
    ("personio.de", "personio"),
    ("personio.com", "personio"),
    ("jobs.personio", "personio"),
    ("stepstone.de", "stepstone"),
    ("smartrecruiters.com", "smartrecruiters"),
    ("jobs.smartrecruiters.com", "smartrecruiters"),
    ("successfactors", "successfactors"),
    ("sap.com", "successfactors"),
    ("taleo.net", "taleo"),
    ("icims.com", "icims"),
    ("bamboohr.com", "bamboohr"),
    ("teamtailor.com", "teamtailor"),
    ("recruitee.com", "recruitee"),
    ("softgarden.io", "softgarden"),
    ("softgarden.de", "softgarden"),
    ("join.com", "join"),
    ("onlyfy.com", "onlyfy",),
    ("umantis.com", "umantis"),
    ("kenoby.com", "kenoby"),
    ("jobvite.com", "jobvite"),
    ("greenhouse-support", "greenhouse"),
]

# ATS keys that have a Jobhuntsaver adapter.
SUPPORTED_ATS = {
    "greenhouse",
    "lever",
    "ashby",
    "indeed",
    "linkedin",
    "workday",
    "personio",
    "stepstone",
    "smartrecruiters",
    "successfactors",
}


class ATSDetector:
    @staticmethod
    def detect(application_url: str) -> str:
        if not application_url:
            return "unknown"
        url_lower = application_url.lower()
        for domain, ats in ATS_FINGERPRINTS:
            if domain in url_lower:
                return ats
        return "unknown"


def classify_ats_support(ats: str, application_url: str = "") -> tuple[str, str]:
    """Return (support_class, human_note).

    support_class: supported | known_unsupported | unknown | empty_url
    """
    if not (application_url or "").strip() and ats in {"", "unknown"}:
        return "empty_url", "Keine Bewerbungs-URL — bitte manuell recherchieren."
    if ats in SUPPORTED_ATS:
        return "supported", "Automatisierung verfügbar (Dry-Run-Guard bleibt aktiv)."
    if ats != "unknown":
        return (
            "known_unsupported",
            f"ATS erkannt ({ats}), aber kein Adapter — Job behalten und manuell öffnen.",
        )
    return (
        "unknown",
        "ATS unbekannt — externe Karriereseite wahrscheinlich. Manuell öffnen/abschließen.",
    )


def ats_coverage_bucket(ats: str) -> str:
    if ats in SUPPORTED_ATS:
        return "supported"
    if ats and ats != "unknown":
        return "detected_unsupported"
    return "unknown"
