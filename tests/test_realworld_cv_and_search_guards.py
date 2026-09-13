"""Regression tests for real-world packaged-EXE defects."""

from __future__ import annotations

from core.config import ApplicationProfile, AppConfig, empty_app_config
from core.cv_parser import parse_cv_text
from core.job_title_suggestions import suggest_job_titles
from core.location import _city_from_address
from core.source_health import SourceHealthStatus
from desktop.services.profile_merge import SOURCE_CV, plan_personal_import


def test_personal_data_from_profile_section() -> None:
    text = """
Lebenslauf

Persönliche Daten
Erika Beispiel
Beispielweg 5
80331 München
erika.beispiel@example.com
+49 170 1112233

Berufserfahrung
Kundenberater

Weitere Kenntnisse
Kundenorientierung
Beschwerdemanagement
ClinicDesk (Zahnarztpraxis-Software)

Sprachen
Deutsch C2
Englisch B2

Führerschein
B
"""
    parsed = parse_cv_text(text)
    personal = parsed["personal"]
    assert personal.get("first_name") == "Erika"
    assert personal.get("last_name") == "Beispiel"
    assert personal.get("postal_code") == "80331"
    assert personal.get("city") == "München"
    assert "Beispielweg" in (personal.get("street") or personal.get("address") or "")
    assert parsed["confidence"]["personal"] != "Nicht erkannt"
    assert "Kundenorientierung" in parsed["skills"]
    soft = " | ".join(parsed["software"]).lower()
    assert "clinicdesk" in soft
    assert soft.count("clinicdesk") == 1
    assert "kundenorientierung" not in soft


def test_software_paren_not_duplicated() -> None:
    text = """
Max Test
EDV-Kenntnisse
ClinicDesk (zentraler Abrechnungsassistent)
NovaDesk Backoffice (Versandplattform)
MS Office
"""
    parsed = parse_cv_text(text)
    joined = " || ".join(parsed["software"])
    assert joined.lower().count("clinicdesk") == 1
    assert joined.lower().count("novadesk") == 1


def test_missing_personal_does_not_clear_existing_profile() -> None:
    app = ApplicationProfile(
        first_name="Anna",
        last_name="Bestehend",
        street="Alte Straße 1",
        postal_code="10115",
        city="Berlin",
        address="Alte Straße 1, 10115 Berlin",
        email="anna@example.com",
        phone="+491234",
        field_origins={
            "first_name": SOURCE_CV,
            "last_name": SOURCE_CV,
            "street": SOURCE_CV,
            "postal_code": SOURCE_CV,
            "city": SOURCE_CV,
            "address": SOURCE_CV,
            "email": SOURCE_CV,
            "phone": SOURCE_CV,
        },
    )
    # Incoming parse failed for address/name — only email found.
    incoming = {"email": "neu@example.com"}
    plan = plan_personal_import(app, incoming, mode="replace")
    assert plan.updates.get("email") == "neu@example.com"
    assert plan.updates.get("street", "MISSING") != ""
    assert "street" not in plan.updates or plan.updates["street"]
    assert not any("leeren" in x for x in plan.will_replace)


def test_empty_queries_status_is_not_ok_empty() -> None:
    assert SourceHealthStatus.EMPTY_QUERY.value == "EMPTY_QUERY"
    status = SourceHealthStatus.from_outcome(
        jobs_found=0, error="No search queries configured", source_id="indeed"
    )
    assert status == SourceHealthStatus.EMPTY_QUERY
    assert status != SourceHealthStatus.OK_EMPTY


def test_build_queries_empty_without_titles() -> None:
    from app.main import build_queries

    cfg = empty_app_config()
    cfg.profile.jobs.desired_titles = []
    cfg.profile.jobs.alternative_titles = []
    cfg.profile.location.home_address = "Berlin"
    assert build_queries(cfg) == []


def test_job_title_suggestions_differ_by_profile() -> None:
    sales = parse_cv_text(
        """
A Sales Person
Berufserfahrung
Kundenberater
Weitere Kenntnisse
Kundenberatung, Verkauf
"""
    )
    office = parse_cv_text(
        """
B Office Person
Berufserfahrung
Sachbearbeiter Rechnungswesen
Weitere Kenntnisse
Buchhaltung, DATEV, Rechnungsprüfung
"""
    )
    s1 = suggest_job_titles(sales)
    s2 = suggest_job_titles(office)
    assert s1["desired"] != s2["desired"]
    assert any("Kunden" in t or "Customer" in t for t in s1["desired"] + s1["alternative"])
    assert any("Sachbearbeit" in t or "Backoffice" in t or "kaufmännisch" in t for t in s2["desired"] + s2["alternative"])


def test_multi_city_home_uses_first_city_only() -> None:
    assert _city_from_address("Berlin / Hamburg") == "Berlin"
    assert _city_from_address("München und Köln") == "München"


def test_build_queries_multi_city_uses_single_city() -> None:
    """Board queries must not send 'Berlin / Hamburg' as the location string."""
    from app.main import build_queries, _search_location

    assert _search_location("Berlin / Hamburg") == "Berlin"
    assert _search_location("Musterstraße 1, 12345 Musterstadt, Deutschland") == "Musterstadt"

    cfg = empty_app_config()
    cfg.profile.jobs.desired_titles = ["Sachbearbeiter"]
    cfg.profile.jobs.alternative_titles = []
    cfg.profile.location.home_address = "Berlin / Hamburg"
    cfg.profile.location.allow_remote_germany = False
    queries = build_queries(cfg)
    assert queries
    assert all(q.location == "Berlin" for q in queries)
    assert not any("/" in q.location or "Hamburg" in q.location for q in queries)


def test_run_pipeline_empty_queries_marks_sources() -> None:
    from app.main import run_pipeline

    cfg = empty_app_config()
    cfg.profile.jobs.desired_titles = []
    cfg.profile.location.home_address = ""
    cfg.profile.location.allow_remote_germany = False
    stats = run_pipeline(cfg, mode="search_only")
    assert stats.get("config_error") == "empty_queries"
    assert stats.get("total") == 0
    # No source should pretend OK_EMPTY for a config problem.
    for src, info in (stats.get("source_results") or {}).items():
        assert info["status"] in {
            SourceHealthStatus.EMPTY_QUERY.value,
            SourceHealthStatus.PLACEHOLDER.value,
        }, src
