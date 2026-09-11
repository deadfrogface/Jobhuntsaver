"""Cancel generation must invalidate late-registered BA enrich pools."""

from __future__ import annotations

from core.cancel import (
    cancel_active_searches,
    current_cancel_generation,
    searches_cancelled,
)


def test_cancel_bumps_generation():
    g0 = current_cancel_generation()
    cancel_active_searches()
    g1 = current_cancel_generation()
    assert g1 != g0
    assert searches_cancelled(g0) is True
    assert searches_cancelled(g1) is False
