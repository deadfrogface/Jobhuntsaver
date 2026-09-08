"""ATS detection from application URLs.

Adapted and extended from AutoApply core/filter.py detect_ats (MIT).
"""

from __future__ import annotations

ATS_FINGERPRINTS: list[tuple[str, str]] = [
    ("boards.greenhouse.io", "greenhouse"),
    ("greenhouse.io", "greenhouse"),
    ("jobs.lever.co", "lever"),
    ("lever.co", "lever"),
    ("myworkdayjobs.com", "workday"),
    ("workday.com", "workday"),
    ("ashbyhq.com", "ashby"),
    ("jobs.ashbyhq.com", "ashby"),
    ("linkedin.com/jobs", "linkedin"),
    ("linkedin.com", "linkedin"),
    ("indeed.com", "indeed"),
    ("de.indeed.com", "indeed"),
    ("personio.de", "personio"),
    ("personio.com", "personio"),
    ("jobs.personio", "personio"),
    ("stepstone.de", "stepstone"),
    ("smartrecruiters.com", "smartrecruiters"),
    ("successfactors", "successfactors"),
    ("sap.com", "successfactors"),
    ("taleo.net", "taleo"),
    ("icims.com", "icims"),
]


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
