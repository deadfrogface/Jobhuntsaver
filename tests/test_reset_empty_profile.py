"""Reset profile must persist EMPTY_PROFILE — no stale rehydration."""

from __future__ import annotations

from pathlib import Path

from core.config import (
    EMPTY_PROFILE,
    ApplicationProfile,
    LanguageEntry,
    QualificationsConfig,
    SourcedText,
    empty_application_profile,
    empty_qualifications,
    load_config,
    save_config,
)
from desktop.services.profile_merge import (
    SOURCE_CV,
    SOURCE_MANUAL,
    clear_all_qualifications,
    clear_complete_application,
)


def test_empty_profile_helpers():
    app = empty_application_profile()
    assert app.first_name == ""
    assert app.email == ""
    assert app.answers == {}
    assert app.field_origins == {}
    assert app.country == "DE"
    assert EMPTY_PROFILE.first_name == ""
    assert empty_qualifications().skills == []


def test_clear_complete_application_wipes_all_fields():
    app = ApplicationProfile(
        first_name="Anna",
        last_name="Alpha",
        email="anna.alpha@example.com",
        phone="+49 1",
        street="X",
        postal_code="10115",
        city="Berlin",
        cv_path="/tmp/cv.pdf",
        answers={"q1": "yes"},
        field_origins={"first_name": SOURCE_CV},
        education="Bachelor",
        languages="Deutsch",
    )
    cleared = clear_complete_application(app)
    assert cleared.first_name == ""
    assert cleared.last_name == ""
    assert cleared.email == ""
    assert cleared.cv_path == ""
    assert cleared.answers == {}
    assert cleared.field_origins == {}
    assert cleared.education == ""
    assert cleared.country == "DE"


def test_reset_empty_persists_and_reloads(tmp_path: Path):
    """Save filled profile, reset to empty, reload — must stay empty (no example refill)."""
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    profile_path = cfg_dir / "profile.yaml"
    application_path = cfg_dir / "application_profile.yaml"
    settings_path = cfg_dir / "settings.yaml"

    root = Path(__file__).resolve().parents[1]
    cfg = load_config(
        profile_path=root / "config" / "profile.yaml.example",
        application_path=root / "config" / "application_profile.yaml.example",
        settings_path=root / "config" / "settings.yaml.example",
        root=tmp_path,
    )
    cfg.application.first_name = "Anna"
    cfg.application.last_name = "Alpha"
    cfg.application.email = "anna.alpha@example.com"
    cfg.application.cv_path = str(tmp_path / "cvs" / "a.pdf")
    cfg.application.answers = {"eligible": "yes"}
    cfg.application.field_origins = {"first_name": SOURCE_CV}
    cfg.profile.qualifications = QualificationsConfig(
        languages=[LanguageEntry(language="Französisch", level="B1", source=SOURCE_CV)],
        skills=[SourcedText(value="Buchhaltung", source=SOURCE_CV)],
        software=[SourcedText(value="DATEV", source=SOURCE_MANUAL)],
    )
    save_config(
        cfg,
        profile_path=profile_path,
        application_path=application_path,
        settings_path=settings_path,
    )

    # Simulate full reset
    cfg.profile.qualifications = clear_all_qualifications()
    cfg.application = clear_complete_application(cfg.application)
    save_config(
        cfg,
        profile_path=profile_path,
        application_path=application_path,
        settings_path=settings_path,
    )

    reloaded = load_config(
        profile_path=profile_path,
        application_path=application_path,
        settings_path=settings_path,
        root=tmp_path,
        strip_placeholders=True,
    )
    assert reloaded.application.first_name == ""
    assert reloaded.application.last_name == ""
    assert reloaded.application.email == ""
    assert reloaded.application.cv_path == ""
    assert reloaded.application.answers == {}
    assert reloaded.application.field_origins == {}
    assert reloaded.profile.qualifications.languages == []
    assert reloaded.profile.qualifications.skills == []
    assert reloaded.profile.qualifications.software == []


def test_empty_yaml_not_rehydrated_from_examples(tmp_path: Path):
    """Existing empty AppData YAML must not fall back to *.example content."""
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "profile.yaml").write_text("{}\n", encoding="utf-8")
    (cfg_dir / "application_profile.yaml").write_text("{}\n", encoding="utf-8")
    (cfg_dir / "settings.yaml").write_text("dry_run: true\n", encoding="utf-8")

    cfg = load_config(
        profile_path=cfg_dir / "profile.yaml",
        application_path=cfg_dir / "application_profile.yaml",
        settings_path=cfg_dir / "settings.yaml",
        root=tmp_path,
    )
    assert cfg.application.first_name == ""
    assert cfg.application.email == ""
    assert cfg.profile.qualifications.skills == []


def test_config_service_clear_cv_storage(tmp_path: Path, monkeypatch):
    from desktop.services import ConfigService

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    svc = ConfigService()
    cvs = svc.dirs["cvs"]
    fake = cvs / "persona.pdf"
    fake.write_bytes(b"%PDF-fake")
    meta = svc.load_meta()
    meta["cv_variants"] = [{"label": "x", "path": str(fake)}]
    svc.save_meta(meta)

    svc.clear_cv_storage()
    assert list(cvs.iterdir()) == []
    assert svc.load_meta().get("cv_variants") == []


def test_config_service_reset_to_empty_profile(tmp_path, monkeypatch):
    from desktop.services import ConfigService
    from core.config import EMPTY_PROFILE

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    svc = ConfigService()
    cfg = svc.load()
    cfg.application.first_name = "Anna"
    cfg.application.email = "anna.alpha@example.com"
    cfg.application.cv_path = str(tmp_path / "cvs" / "x.pdf")
    (svc.dirs["cvs"] / "x.pdf").write_bytes(b"%PDF")
    svc.save(cfg)

    emptied = svc.reset_to_empty_profile()
    assert emptied.application.first_name == EMPTY_PROFILE.first_name
    assert emptied.application.email == ""
    assert emptied.application.cv_path == ""
    assert emptied.profile.qualifications.skills == []
    assert list(svc.dirs["cvs"].iterdir()) == []

    again = svc.load()
    assert again.application.first_name == ""
    assert again.application.email == ""
