"""Search preferences vs applicant profile — keep these domains separate.

SearchPreferences (``core.config.SearchPreferences``, formerly ProfileConfig)
---------------------------------------------------------------------------
Controls *where/what* to search: ``location.home_address``, commute radius,
desired titles, employment model, company filters. Used by search adapters
and distance filtering — not for filling application forms.

``ProfileConfig`` remains a backward-compatible alias of ``SearchPreferences``.

ApplicantProfile (``ApplicationProfile`` in ``core.config``)
------------------------------------------------------------
Personal data for ATS form fill: name, street, city, email, phone, CV path,
answers. Must not silently overwrite search ``home_address``.

Sync rule
---------
Optional UI may copy applicant street/city into ``location.home_address``
**only** when the user explicitly checks the opt-in checkbox (default: off).
"""

from __future__ import annotations

from core.config import (
    ApplicationProfile,
    ProfileConfig,
    SearchPreferences,
    empty_search_preferences,
)

# Intent-named alias for form-fill PII (same class as ApplicationProfile).
ApplicantProfile = ApplicationProfile

__all__ = [
    "SearchPreferences",
    "ApplicantProfile",
    "ProfileConfig",
    "ApplicationProfile",
    "empty_search_preferences",
]
