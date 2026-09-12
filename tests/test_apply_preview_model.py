"""ApplicationPreview model fields used by pre-submit UI."""

from __future__ import annotations

from apply.preview import ApplicationPreview, build_application_preview
from core.config import AppConfig, ApplicationProfile, SettingsConfig
from core.models import Job


def test_preview_model_submit_allowed_false_and_identity():
    cfg = AppConfig(
        application=ApplicationProfile(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            phone="+49 151 000",
            street="Testweg 1",
            postal_code="10115",
            city="Berlin",
            country="DE",
            date_of_birth="1815-12-10",
            answers={"notice_period": "3 Monate", "work_auth": "EU"},
            cv_path="",
        ),
        settings=SettingsConfig(dry_run=True, mode="review_before_submit"),
    )
    job = Job(
        id="j1",
        source="indeed",
        title="Sachbearbeiter",
        company="Example GmbH",
        match_score=82,
        application_url="https://boards.greenhouse.io/example/jobs/1",
    )
    preview = build_application_preview(job, cfg)
    assert isinstance(preview, ApplicationPreview)
    assert preview.submit_allowed is False
    assert preview.will_submit is False
    assert preview.dry_run is True
    assert preview.match_score == 82
    assert preview.form_values["Vorname"] == "Ada"
    assert preview.form_values["Nachname"] == "Lovelace"
    assert preview.form_values["E-Mail"] == "ada@example.com"
    assert preview.form_values["PLZ"] == "10115"
    assert preview.form_values["Ort"] == "Berlin"
    assert preview.intended_answers["notice_period"] == "3 Monate"
    assert "notice_period" in preview.screening_questions
    assert isinstance(preview.unknown_fields, list)
    text = preview.text_report()
    assert "Ada" in text
    assert "Match: 82%" in text
    assert "submit_allowed" in text.lower() or "NEIN" in text
    data = preview.to_dict()
    assert data["submit_allowed"] is False
    assert data["match_score"] == 82
    assert "intended_answers" in data


def test_preview_submit_allowed_only_when_auto_and_not_dry():
    cfg = AppConfig(
        application=ApplicationProfile(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
        ),
        settings=SettingsConfig(dry_run=False, mode="fully_automatic", automatic_submission=True),
    )
    job = Job(
        id="j2",
        title="Role",
        company="Co",
        application_url="https://boards.greenhouse.io/example/jobs/2",
    )
    preview = build_application_preview(job, cfg)
    assert preview.will_submit is True
    assert preview.submit_allowed is True


def test_preview_submit_blocked_when_auto_submit_disabled():
    cfg = AppConfig(
        application=ApplicationProfile(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
        ),
        settings=SettingsConfig(
            dry_run=False,
            mode="fully_automatic",
            automatic_submission=False,
        ),
    )
    job = Job(
        id="j3",
        title="Role",
        company="Co",
        application_url="https://boards.greenhouse.io/example/jobs/3",
    )
    preview = build_application_preview(job, cfg)
    assert preview.will_submit is False
    assert preview.submit_allowed is False
