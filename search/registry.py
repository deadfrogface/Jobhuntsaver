"""Search source registry."""

from __future__ import annotations

from search.base import JobSource
from search.bundesagentur import BundesagenturSource
from search.company_sites import CompanySitesSource
from search.indeed import IndeedSource
from search.linkedin import LinkedInSearchSource
from search.stepstone import StepstoneSource
from search.xing import XingSource


def build_sources(enabled: list[str]) -> list[JobSource]:
    registry: dict[str, JobSource] = {
        "bundesagentur": BundesagenturSource(),
        "indeed": IndeedSource(),
        "linkedin": LinkedInSearchSource(),
        "stepstone": StepstoneSource(),
        "xing": XingSource(),
        "company_sites": CompanySitesSource(),
    }
    return [registry[name] for name in enabled if name in registry]
