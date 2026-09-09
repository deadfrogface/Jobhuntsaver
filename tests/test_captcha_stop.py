"""CAPTCHA must stop the AutoApply loop (never bypass)."""

from __future__ import annotations

from apply.base import ApplyResult


def test_captcha_result_stops_loop_semantics():
    """Document the pipeline contract: captcha_detected → break, not continue."""
    results = [
        ApplyResult(success=False, captcha_detected=True, error_message="CAPTCHA"),
        ApplyResult(success=True, submitted=True),
    ]
    applied = 0
    captcha = 0
    for result in results:
        if result.captcha_detected:
            captcha += 1
            break
        if result.submitted:
            applied += 1
    assert captcha == 1
    assert applied == 0  # second job never processed
