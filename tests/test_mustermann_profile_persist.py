"""Regression: real Max Mustermann profiles must persist; demo email still strips."""

from __future__ import annotations

import os
from pathlib import Path

from core.config import (
    EXAMPLE_APPLICATION_MARKERS,
    ApplicationProfile,
    strip_example_application,
)
from desktop.services import ConfigService


def test_strip_example_keeps_real_mustermann_with_real_email():
    app = ApplicationProfile(
        first_name="Max",
        last_name="Mustermann",
        email="max.real@example.org",
        phone="+491701234567",
        cv_path="cvs/max.pdf",
    )
    kept = strip_example_application(app)
    assert kept.first_name == "Max"
    assert kept.last_name == "Mustermann"
    assert kept.email == "max.real@example.org"
    assert kept.phone == "+491701234567"
    assert kept.cv_path == "cvs/max.pdf"


def test_strip_example_clears_demo_email_fingerprint():
    app = ApplicationProfile(
        first_name="Max",
        last_name="Mustermann",
        email=EXAMPLE_APPLICATION_MARKERS["email"],
        phone="+491701234567",
        cv_path="cvs/demo.pdf",
    )
    cleared = strip_example_application(app)
    assert cleared.first_name == ""
    assert cleared.last_name == ""
    assert cleared.email == ""
    assert cleared.phone == ""
    assert cleared.cv_path == ""


def test_strip_example_keeps_owned_mustermann_demo_email():
    """CV/manual ownership must survive reload even with the legacy demo email."""
    app = ApplicationProfile(
        first_name="Max",
        last_name="Mustermann",
        email=EXAMPLE_APPLICATION_MARKERS["email"],
        phone="+491701234567",
        street="Musterstraße 1",
        postal_code="12345",
        city="Berlin",
        field_origins={
            "first_name": "cv",
            "last_name": "cv",
            "email": "cv",
            "phone": "cv",
            "street": "cv",
            "postal_code": "cv",
            "city": "cv",
        },
    )
    kept = strip_example_application(app)
    assert kept.first_name == "Max"
    assert kept.email == EXAMPLE_APPLICATION_MARKERS["email"]
    assert kept.phone == "+491701234567"
    assert kept.street == "Musterstraße 1"


def test_mustermann_cv_import_survives_save_load(tmp_path: Path):
    from core.config import load_config, save_config, empty_app_config
    from core.cv_parser import parse_cv_text
    from desktop.services.profile_merge import (
        apply_personal_updates,
        personal_from_parsed,
        plan_personal_import,
    )

    root = tmp_path
    (root / "config").mkdir()
    cfg = empty_app_config(root=root)
    parsed = parse_cv_text(
        """Max Mustermann
Musterstraße 1
12345 Berlin
max.mustermann@example.com
+49 170 1234567
"""
    )
    incoming = personal_from_parsed(parsed)
    plan = plan_personal_import(cfg.application, incoming, mode="replace")
    apply_personal_updates(cfg.application, plan.updates, source="cv")
    assert cfg.application.email == "max.mustermann@example.com"
    assert (cfg.application.field_origins or {}).get("email") == "cv"

    profile = root / "config" / "profile.yaml"
    application = root / "config" / "application_profile.yaml"
    settings = root / "config" / "settings.yaml"
    save_config(cfg, profile_path=profile, application_path=application, settings_path=settings)
    loaded = load_config(
        profile_path=profile, application_path=application, settings_path=settings, root=root
    )
    assert loaded.application.first_name == "Max"
    assert loaded.application.last_name == "Mustermann"
    assert loaded.application.email == "max.mustermann@example.com"
    assert loaded.application.phone == "+49 170 1234567"
    assert loaded.application.city == "Berlin"


def test_config_service_save_reload_keeps_mustermann(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    svc = ConfigService()
    cfg = svc.load()
    cfg.application.first_name = "Max"
    cfg.application.last_name = "Mustermann"
    cfg.application.email = "max.bewerbung@example.org"
    cfg.application.phone = "+491701234567"
    saved = svc.save(cfg)
    assert saved.application.first_name == "Max"
    assert saved.application.last_name == "Mustermann"
    assert saved.application.email == "max.bewerbung@example.org"
    reloaded = svc.load()
    assert reloaded.application.first_name == "Max"
    assert reloaded.application.email == "max.bewerbung@example.org"
    yaml_text = (tmp_path / "Jobhuntsaver" / "config" / "application_profile.yaml").read_text(
        encoding="utf-8"
    )
    assert "Max" in yaml_text
    assert "Mustermann" in yaml_text
