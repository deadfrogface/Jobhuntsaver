"""ATS detection from application URLs.

Adapted and extended from AutoApply core/filter.py detect_ats (MIT).
"""

from __future__ import annotations

from urllib.parse import urlparse

# Longer / more specific fingerprints first. Match host/path shapes only —
# never bare marketing domains or query-string substrings.
ATS_FINGERPRINTS: list[tuple[str, str]] = [
    ("boards.greenhouse.io", "greenhouse"),
    ("job-boards.greenhouse.io", "greenhouse"),
    ("jobs.lever.co", "lever"),
    ("myworkdayjobs.com", "workday"),
    ("wd1.myworkdaysite.com", "workday"),
    ("wd3.myworkdaysite.com", "workday"),
    ("wd5.myworkdaysite.com", "workday"),
    ("jobs.ashbyhq.com", "ashby"),
    ("linkedin.com/jobs", "linkedin"),
    ("de.indeed.com", "indeed"),
    ("indeed.com/viewjob", "indeed"),
    ("indeed.com/rc/clk", "indeed"),
    ("indeed.com/jobs", "indeed"),
    ("personio.de/job", "personio"),
    ("personio.com/job", "personio"),
    ("jobs.personio.de", "personio"),
    ("jobs.personio.com", "personio"),
    ("stepstone.de/stellenangebote", "stepstone"),
    ("stepstone.de/job", "stepstone"),
    ("jobs.smartrecruiters.com", "smartrecruiters"),
    ("smartrecruiters.com/job", "smartrecruiters"),
    ("taleo.net", "taleo"),
    ("icims.com", "icims"),
    ("bamboohr.com", "bamboohr"),
    ("teamtailor.com", "teamtailor"),
    ("recruitee.com", "recruitee"),
    ("softgarden.io", "softgarden"),
    ("onlyfy.com", "onlyfy"),
    ("umantis.com", "umantis"),
    ("kenoby.com", "kenoby"),
    ("jobvite.com", "jobvite"),
]

# Mature adapters: safe field fill + dry-run/submit guard.
SUPPORTED_ATS = {
    "greenhouse",
    "lever",
    "ashby",
    "indeed",
    "linkedin",
    "workday",
}

# Thin DE / multi-page adapters: fill what we can, prefer review before submit.
PARTIALLY_SUPPORTED_ATS = {
    "personio",
    "stepstone",
    "smartrecruiters",
    "successfactors",
}

# Any ATS with an applier module (full or partial).
APPLIER_ATS = SUPPORTED_ATS | PARTIALLY_SUPPORTED_ATS


def _host_path(url: str) -> tuple[str, str]:
    """Return (netloc, path) lowercased — never query/fragment."""
    try:
        parsed = urlparse(url.strip())
    except Exception:
        raw = url.lower().split("?", 1)[0].split("#", 1)[0]
        if "/" in raw:
            host, _, path = raw.partition("/")
            return host, "/" + path
        return raw, ""
    return (parsed.netloc or "").lower(), (parsed.path or "").lower()


def _host_matches(host: str, fingerprint_host: str) -> bool:
    return host == fingerprint_host or host.endswith("." + fingerprint_host)


def _fingerprint_match(host: str, path: str, fingerprint: str) -> bool:
    if "/" in fingerprint:
        fp_host, _, fp_path = fingerprint.partition("/")
        if not _host_matches(host, fp_host):
            return False
        return ("/" + fp_path) in path or path.startswith("/" + fp_path)
    return _host_matches(host, fingerprint)


def _detect_successfactors(host: str, path: str) -> bool:
    """Career/PM hosts only — not bare successfactors.com marketing pages."""
    if "sapsf." in host or host.endswith("sapsf.eu") or host.endswith("sapsf.com"):
        return True
    if "performancemanager" in host and "successfactors" in host:
        return True
    if "successfactors." in host and any(
        token in path for token in ("/career", "/sf", "/job", "/jobreq", "/jobreqcareer")
    ):
        return True
    return False


class ATSDetector:
    @staticmethod
    def detect(application_url: str) -> str:
        if not application_url:
            return "unknown"
        host, path = _host_path(application_url)
        if _detect_successfactors(host, path):
            return "successfactors"
        for domain, ats in ATS_FINGERPRINTS:
            if _fingerprint_match(host, path, domain):
                return ats
        return "unknown"


def classify_ats_support(ats: str, application_url: str = "") -> tuple[str, str]:
    """Return (support_class, human_note).

    support_class: supported | partially_supported | known_unsupported | unknown | empty_url
    """
    if not (application_url or "").strip() and ats in {"", "unknown"}:
        return "empty_url", "Keine Bewerbungs-URL — bitte manuell recherchieren."
    if ats in SUPPORTED_ATS:
        return "supported", "Automatisierung verfügbar (Dry-Run-Guard bleibt aktiv)."
    if ats in PARTIALLY_SUPPORTED_ATS:
        return (
            "partially_supported",
            "Teilweise Automatisierung — Formular vorausfüllen, Abschluss prüfen/manuell.",
        )
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
    if ats in PARTIALLY_SUPPORTED_ATS:
        return "partially_supported"
    if ats and ats != "unknown":
        return "detected_unsupported"
    return "unknown"
