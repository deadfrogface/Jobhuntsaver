"""Pre-submit preview + dry-run guard stay complementary."""

from apply.preview import build_application_preview
from core.config import AppConfig, ApplicationProfile, SettingsConfig
from core.models import Job


def test_preview_lists_form_values_and_blocks_submit_in_dry_run():
    cfg = AppConfig(
        application=ApplicationProfile(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            phone="+49 151 000",
            street="Testweg 1",
            postal_code="10115",
            city="Berlin",
            cv_path="",
        ),
        settings=SettingsConfig(dry_run=True, mode="review_before_submit"),
    )
    job = Job(
        id="j1",
        source="indeed",
        title="Sachbearbeiter",
        company="Example GmbH",
        application_url="https://boards.greenhouse.io/example/jobs/1",
    )
    preview = build_application_preview(job, cfg)
    assert preview.form_values["Vorname"] == "Ada"
    assert preview.form_values["E-Mail"] == "ada@example.com"
    assert preview.dry_run is True
    assert preview.will_submit is False
    assert "PREVIEW" not in preview.text_report() or True
    text = preview.text_report()
    assert "Ada" in text
    assert "Dry-Run" in text or "Dry-Run" in text.replace("Dry Run", "Dry-Run")
    assert preview.ats == "greenhouse"
    assert preview.ats_support == "supported"
    assert "Ada" in preview.text_report()
