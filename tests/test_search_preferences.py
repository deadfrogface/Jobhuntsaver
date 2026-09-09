"""SearchPreferences is the real dataclass; ProfileConfig remains an alias."""

from dataclasses import asdict

from core.config import (
    ApplicationProfile,
    ProfileConfig,
    SearchPreferences,
    empty_search_preferences,
    strip_example_placeholders,
)
from core.search_preferences import ApplicantProfile, SearchPreferences as SPAlias


def test_search_preferences_is_dataclass_not_mere_alias_target():
    prefs = empty_search_preferences()
    assert isinstance(prefs, SearchPreferences)
    assert prefs.location.country == "DE"
    assert prefs.jobs.desired_titles == []


def test_profile_config_alias_is_same_class():
    assert ProfileConfig is SearchPreferences
    assert SPAlias is SearchPreferences


def test_applicant_profile_alias():
    assert ApplicantProfile is ApplicationProfile


def test_search_preferences_distinct_from_applicant_profile():
    prefs = empty_search_preferences()
    applicant = ApplicationProfile(first_name="Ada", street="Main 1")
    assert prefs.location.home_address == ""
    assert applicant.street == "Main 1"
    # Mutating applicant must not touch search prefs object fields
    applicant.city = "Berlin"
    assert not hasattr(prefs, "street")


def test_strip_example_placeholders_returns_search_preferences():
    prefs = empty_search_preferences()
    prefs.qualifications.skills = []  # type: ignore[assignment]
    cleaned = strip_example_placeholders(prefs)
    assert isinstance(cleaned, SearchPreferences)
    assert asdict(cleaned.location)["country"] == "DE"
