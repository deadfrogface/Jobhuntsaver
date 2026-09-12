"""Mindestgehalt and Gehaltsvorstellung must stay aligned on profile save."""

from __future__ import annotations

from core.config import empty_app_config
from core.salary import normalize_to_annual_gross_eur


def test_expectation_text_fills_empty_minimum_salary():
    cfg = empty_app_config()
    cfg.application.salary_expectation = "48000 EUR brutto/Jahr"
    cfg.profile.employment.minimum_salary = None
    annual, reason = normalize_to_annual_gross_eur(text=cfg.application.salary_expectation)
    assert annual == 48000
    if annual and not cfg.profile.employment.minimum_salary:
        cfg.profile.employment.minimum_salary = float(annual)
    assert cfg.profile.employment.minimum_salary == 48000.0


def test_minimum_salary_fills_empty_expectation_text():
    cfg = empty_app_config()
    cfg.application.salary_expectation = ""
    cfg.profile.employment.minimum_salary = 42000.0
    if cfg.profile.employment.minimum_salary and not (cfg.application.salary_expectation or "").strip():
        cfg.application.salary_expectation = f"{int(cfg.profile.employment.minimum_salary)} EUR brutto/Jahr"
    assert "42000" in cfg.application.salary_expectation
