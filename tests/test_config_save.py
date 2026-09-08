"""Tests for config save/load used by the desktop ConfigService."""

from __future__ import annotations

from pathlib import Path

from core.config import load_config, save_config


def test_save_and_reload_config(tmp_path: Path) -> None:
    cfg = load_config()
    cfg.application.first_name = "Ada"
    cfg.application.street = "Testweg 1"
    cfg.application.postal_code = "12345"
    cfg.application.city = "Berlin"
    cfg.application.country = "DE"
    cfg.application.sync_address()
    cfg.settings.dry_run = True
    cfg.settings.mode = "search_only"

    profile = tmp_path / "profile.yaml"
    application = tmp_path / "application_profile.yaml"
    settings = tmp_path / "settings.yaml"
    save_config(
        cfg,
        profile_path=profile,
        application_path=application,
        settings_path=settings,
    )
    assert profile.exists()
    assert application.exists()
    assert settings.exists()

    loaded = load_config(
        profile_path=profile,
        application_path=application,
        settings_path=settings,
        root=tmp_path,
    )
    assert loaded.application.first_name == "Ada"
    assert "Berlin" in loaded.application.address
    assert loaded.settings.dry_run is True
    assert loaded.settings.mode == "search_only"
