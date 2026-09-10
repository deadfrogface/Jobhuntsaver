"""Windows paths with spaces and umlauts for Database + ConfigService."""

from __future__ import annotations

from pathlib import Path

from core.config import load_config, save_config
from core.database import Database
from core.models import Job


def test_database_path_with_spaces_and_umlauts(tmp_path: Path):
    base = tmp_path / "Job Daten" / "Büro München"
    base.mkdir(parents=True, exist_ok=True)
    db_path = base / "jobs ü.db"
    db = Database(db_path)
    job = Job(
        id="j1",
        source="test",
        source_job_id="1",
        title="Sachbearbeiter",
        company="Beispiel GmbH",
        city="München",
    )
    db.upsert_job(job)
    loaded = db.get_job("j1")
    assert loaded is not None
    assert loaded.city == "München"
    assert db.dashboard_stats()["total_jobs"] == 1


def test_config_service_paths_with_spaces_umlauts(tmp_path, monkeypatch):
    root = tmp_path / "App Data" / "Jobhuntsaver ÄÖÜ"
    monkeypatch.setenv("LOCALAPPDATA", str(root.parent))
    # Force AppData name under umlaut parent by patching ensure_app_dirs
    from desktop import paths as paths_mod

    def fake_dirs():
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

    from desktop.services import ConfigService

    svc = ConfigService()
    cfg = svc.load()
    cfg.application.first_name = "Müller"
    cfg.profile.location.home_address = "Musterstraße 1, München"
    svc.save(cfg)
    again = svc.load()
    assert again.application.first_name == "Müller"
    assert "München" in again.profile.location.home_address

    # Direct YAML roundtrip under unicode path
    profile = root / "config" / "profil ü.yaml"
    application = root / "config" / "bewerbung ü.yaml"
    settings = root / "config" / "settings ü.yaml"
    save_config(
        again,
        profile_path=profile,
        application_path=application,
        settings_path=settings,
    )
    loaded = load_config(
        profile_path=profile,
        application_path=application,
        settings_path=settings,
        root=root,
    )
    assert loaded.application.first_name == "Müller"
