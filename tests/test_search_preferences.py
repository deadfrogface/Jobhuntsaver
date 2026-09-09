"""SearchPreferences is the real dataclass; ProfileConfig remains an alias."""

from core.config import ProfileConfig, SearchPreferences, empty_search_preferences
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
    from core.config import ApplicationProfile

    assert ApplicantProfile is ApplicationProfile
