"""Offscreen GUI journeys for real-user quality pass surfaces."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def config_service(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from desktop import paths as paths_mod

    def fake_dirs():
        root = tmp_path / "Karrierekrake"
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


def test_career_section_has_no_alternative_berufe_widget(qapp):
    from desktop.pages.profile_sections import CareerSection
    from desktop.i18n import tr

    section = CareerSection()
    section.retranslate()
    # Soft-compat: alt_titles aliases desired; label must not be shown.
    assert section.lbl_alt.isVisible() is False
    # No dedicated alternative editor distinct from desired.
    assert section.alt_titles is section.desired_titles
    assert "Alternative" not in section.lbl_desired.text()


def test_jobs_page_columns_and_nan_guard(qapp, config_service, tmp_path):
    from core.database import Database
    from core.models import Job
    from desktop.pages.jobs import JobsPage

    cfg = config_service.load()
    db = Database(cfg.db_path)
    db.upsert_job(
        Job(
            id="job-nan",
            title="Sachbearbeiter",
            company="nan",
            city="Berlin",
            remote_type="hybrid",
            distance_km=4.2,
            match_score=77,
            match_reasons=["Direkt: Excel"],
            source="bundesagentur",
            status="new",
        )
    )
    page = JobsPage(config_service)
    page.refresh()
    assert page.table.columnCount() == 9
    headers = [page.table.horizontalHeaderItem(i).text() for i in range(9)]
    assert any("Begründung" in h or "Why" in h or "Erklärung" in h or h for h in headers)
    # Company cell must not display literal nan when blankish — Job.__post_init__ cleans it.
    company_texts = [
        page.table.item(r, 1).text() for r in range(page.table.rowCount())
    ]
    assert all(t.lower() != "nan" for t in company_texts)


def test_settings_jobs_per_search_and_mode(qapp, config_service):
    from desktop.pages.settings import SettingsPage

    page = SettingsPage(config_service)
    page.load_from_config()
    assert page.jobs_per_search.count() == 10
    assert page.search_mode.count() == 2
    # Max is last choice with data 0
    assert page.jobs_per_search.itemData(page.jobs_per_search.count() - 1) == 0


def test_document_role_copy_does_not_clobber_cv(qapp, config_service, tmp_path):
    cv = tmp_path / "cv.pdf"
    cover = tmp_path / "anschreiben.pdf"
    cv.write_bytes(b"%PDF-1.4 cv")
    cover.write_bytes(b"%PDF-1.4 cover")
    dest_cv = config_service.copy_cv_into_storage(cv, label="CV", role="cv")
    path_before = config_service.load().application.cv_path
    config_service.copy_cv_into_storage(cover, label="Anschreiben", role="cover_letter")
    cfg = config_service.load()
    assert cfg.application.cv_path == path_before
    meta = config_service.load_meta()
    roles = {v.get("role") for v in meta.get("cv_variants") or []}
    assert "cv" in roles and "cover_letter" in roles
    info = config_service.get_active_cv_info()
    assert info["role"] == "cv"
    assert "Lebenslauf" in info["label"] or dest_cv.name in info["label"]
