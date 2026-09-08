"""UI preference persistence and translation coverage."""

from __future__ import annotations

from pathlib import Path

from core.config import load_config, save_config
from desktop.i18n import TRANSLATIONS, TranslationService
from desktop.services import ConfigService
from desktop.theme import resolve_theme, stylesheet_for


def test_translation_keys_match_between_languages():
    assert set(TRANSLATIONS["de"]) == set(TRANSLATIONS["en"])
    assert len(TRANSLATIONS["de"]) > 50


def test_translation_service_switches_language():
    svc = TranslationService("de")
    assert "Einstellung" in svc.t("nav.settings") or svc.t("nav.settings") == "Einstellungen"
    svc.set_language("en")
    assert svc.t("nav.settings") == "Settings"
    assert svc.t("nav.applications") == "Applications"


def test_theme_and_language_persist(tmp_path: Path):
    cfg = load_config(root=tmp_path, strip_placeholders=True)
    cfg.settings.theme = "dark"
    cfg.settings.language = "en"
    cfg.settings.minimize_to_tray = False
    profile = tmp_path / "config" / "profile.yaml"
    application = tmp_path / "config" / "application_profile.yaml"
    settings = tmp_path / "config" / "settings.yaml"
    save_config(cfg, profile_path=profile, application_path=application, settings_path=settings)
    loaded = load_config(
        profile_path=profile,
        application_path=application,
        settings_path=settings,
        root=tmp_path,
    )
    assert loaded.settings.theme == "dark"
    assert loaded.settings.language == "en"
    assert loaded.settings.minimize_to_tray is False


def test_stylesheet_for_light_and_dark():
    light = stylesheet_for("light")
    dark = stylesheet_for("dark")
    assert "QMainWindow" in light and "QMainWindow" in dark
    assert light != dark
    assert resolve_theme("light") == "light"
    assert resolve_theme("dark") == "dark"
    assert resolve_theme("system") in {"light", "dark"}


def test_window_state_persist(tmp_path: Path, monkeypatch):
    # Point AppData-like dirs to tmp via monkeypatch of ensure_app_dirs
    from desktop import paths as paths_mod

    def fake_dirs():
        root = tmp_path / "Jobhuntsaver"
        dirs = {
            "root": root,
            "config": root / "config",
            "data": root / "data",
            "logs": root / "logs",
            "browser_profile": root / "browser_profile",
            "cvs": root / "cvs",
            "cache": root / "cache",
            "cover_letters": root / "cover_letters",
        }
        for p in dirs.values():
            p.mkdir(parents=True, exist_ok=True)
        return dirs

    monkeypatch.setattr(paths_mod, "ensure_app_dirs", fake_dirs)
    monkeypatch.setattr("desktop.services.ensure_app_dirs", fake_dirs)
    svc = ConfigService()
    svc.save_window_state(width=1280, height=800, x=10, y=20, maximized=True)
    state = svc.get_window_state()
    assert state["width"] == 1280
    assert state["height"] == 800
    assert state["maximized"] is True
    assert state["x"] == 10
