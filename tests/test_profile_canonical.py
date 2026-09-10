"""ApplicantProfile canonical fields, low-confidence guard, search home separation."""

from __future__ import annotations

from pathlib import Path

from core.config import (
    ApplicationProfile,
    empty_application_profile,
    load_config,
    save_config,
)
from core.search_preferences import ApplicantProfile
from desktop.services.profile_merge import personal_from_parsed, plan_personal_import


def test_applicant_profile_alias_and_roundtrip(tmp_path: Path):
    assert ApplicantProfile is ApplicationProfile
    app = ApplicationProfile(
        first_name="Ada",
        last_name="Lovelace",
        street="Testweg 1",
        postal_code="10115",
        city="Berlin",
        country="DE",
        email="ada@example.com",
        phone="+49 151 0000000",
        date_of_birth="1815-12-10",
        linkedin_url="https://linkedin.com/in/ada",
        answers={"work_auth": "EU"},
    )
    app.sync_address()
    cfg = load_config(root=tmp_path, strip_placeholders=True)
    cfg.application = app
    profile = tmp_path / "profile.yaml"
    application = tmp_path / "application_profile.yaml"
    settings = tmp_path / "settings.yaml"
    save_config(cfg, profile_path=profile, application_path=application, settings_path=settings)
    loaded = load_config(
        profile_path=profile,
        application_path=application,
        settings_path=settings,
        root=tmp_path,
    )
    assert loaded.application.first_name == "Ada"
    assert loaded.application.last_name == "Lovelace"
    assert loaded.application.street == "Testweg 1"
    assert loaded.application.postal_code == "10115"
    assert loaded.application.city == "Berlin"
    assert loaded.application.email == "ada@example.com"
    assert loaded.application.answers.get("work_auth") == "EU"
    assert "Berlin" in loaded.application.address


def test_low_confidence_personal_does_not_overwrite():
    existing = ApplicationProfile(first_name="Manual", last_name="User", email="manual@example.com")
    parsed = {
        "confidence": {"personal": "low"},
        "uncertain": ["personal"],
        "personal": {
            "first_name": "Garbage",
            "last_name": "Name",
            "street": "Wrong 9",
            "city": "Nowhere",
        },
        "emails": ["cv-hit@example.com"],
        "phones": ["+49 160 111"],
    }
    incoming = personal_from_parsed(parsed)
    assert "first_name" not in incoming
    assert "last_name" not in incoming
    assert "street" not in incoming
    assert incoming.get("email") == "cv-hit@example.com"
    plan = plan_personal_import(existing, incoming, mode="merge")
    # Low-confidence must not push garbage names into updates as forced replaces
    assert plan.updates.get("first_name") != "Garbage"
    assert existing.first_name == "Manual"


def test_search_home_separate_from_address(tmp_path: Path):
    cfg = load_config(root=tmp_path, strip_placeholders=True)
    cfg.application.street = "Bewerbungsstraße 2"
    cfg.application.postal_code = "80331"
    cfg.application.city = "München"
    cfg.application.sync_address()
    cfg.profile.location.home_address = "Suchstraße 9, 10115 Berlin"
    profile = tmp_path / "profile.yaml"
    application = tmp_path / "application_profile.yaml"
    settings = tmp_path / "settings.yaml"
    save_config(cfg, profile_path=profile, application_path=application, settings_path=settings)
    loaded = load_config(
        profile_path=profile,
        application_path=application,
        settings_path=settings,
        root=tmp_path,
    )
    assert "München" in loaded.application.address or loaded.application.city == "München"
    assert "Berlin" in loaded.profile.location.home_address
    assert loaded.application.street != loaded.profile.location.home_address
    blank = empty_application_profile()
    assert blank.first_name == ""
    assert blank.city == ""
