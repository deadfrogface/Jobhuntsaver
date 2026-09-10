"""Offline Qt smoke: navigation, theme, language, pause button."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication  # noqa: E402

from desktop.i18n import i18n, tr  # noqa: E402
from desktop.theme import stylesheet_for  # noqa: E402


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def config_service(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from desktop import paths as paths_mod

    def fake_dirs():
        root = tmp_path / "Jobhuntsaver"
        dirs = {
            "root": root,
            "config": root / "config",
            "data": root / "data",
            "logs": root / "logs",
            "browser_profile": root / "browser_profile",
            "browsers": root / "browsers",
            "cvs": root / "cvs",
            "cache": root / "cache",
            "cover_letters": root / "cover_letters",
        }
        for p in dirs.values():
            p.mkdir(parents=True, exist_ok=True)
        return dirs

    monkeypatch.setattr(paths_mod, "ensure_app_dirs", fake_dirs)
    monkeypatch.setattr("desktop.services.ensure_app_dirs", fake_dirs)
    monkeypatch.setattr(
        "desktop.services.schedule_service.ScheduleService.sync_from_config",
        lambda self: (True, "ok"),
    )
    from desktop.services import ConfigService

    return ConfigService()


def test_qt_smoke_main_window(qapp, config_service, monkeypatch):
    # Avoid system tray / native widgets failing headless
    monkeypatch.setattr("desktop.tray.AppTray.show", lambda self: None)
    monkeypatch.setattr("desktop.tray.AppTray.showMessage", lambda *a, **k: None)

    from desktop.main_window import MainWindow

    win = MainWindow(config_service)
    try:
        assert win.stack.count() >= 6
        for idx in range(win.stack.count()):
            win._navigate(idx)
            assert win.stack.currentIndex() == idx

        # Theme switch
        cfg = config_service.load()
        cfg.settings.theme = "dark"
        config_service.save(cfg)
        win.apply_appearance_from_settings()
        assert "QMainWindow" in stylesheet_for("dark")

        cfg.settings.theme = "light"
        config_service.save(cfg)
        win.apply_appearance_from_settings()

        # Language DE → EN
        i18n.set_language("de")
        win.retranslate_ui()
        assert tr("nav.settings") == "Einstellungen"
        cfg.settings.language = "en"
        config_service.save(cfg)
        win.apply_appearance_from_settings()
        assert tr("nav.settings") == "Settings"

        # Pause button text follows automation_paused
        cfg = config_service.load()
        cfg.settings.automation_paused = False
        config_service.save(cfg)
        win.dashboard.refresh()
        assert win.dashboard.btn_pause.text() == tr("btn.pause_automation")
        win.toggle_automation_paused()
        assert config_service.load().settings.automation_paused is True
        assert win.dashboard.btn_pause.text() == tr("btn.resume_automation")
    finally:
        win.close()
