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
        email="max.real@firma.de",
        phone="+491701234567",
        cv_path="cvs/max.pdf",
    )
    kept = strip_example_application(app)
    assert kept.first_name == "Max"
    assert kept.last_name == "Mustermann"
    assert kept.email == "max.real@firma.de"
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
