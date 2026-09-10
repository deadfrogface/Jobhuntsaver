"""Every ATS applier must never click submit in dry_run."""

from __future__ import annotations

from apply.base import BaseApplier
from apply.manager import APPLIERS


class _ClickTrackingPage:
    def __init__(self) -> None:
        self.click_count = 0

    def wait_for_selector(self, *args, **kwargs):
        return object()

    def query_selector(self, *args, **kwargs):
        page = self

        class _Btn:
            def is_visible(self) -> bool:
                return True

            def click(self) -> None:
                page.click_count += 1

        return _Btn()


def test_dry_run_all_adapters_never_click_submit(monkeypatch):
    page = _ClickTrackingPage()
    clicks_via_patch = {"n": 0}

    # Also patch BaseApplier helpers that would click.
    real_maybe = BaseApplier._maybe_submit

    def wrapped(self, submit_selector: str):
        result = real_maybe(self, submit_selector)
        return result

    monkeypatch.setattr(BaseApplier, "_maybe_submit", wrapped)

    for name, cls in APPLIERS.items():
        page.click_count = 0
        applier = cls(page, dry_run=True, submit=True)
        assert applier.dry_run is True
        result = applier._maybe_submit("button[type='submit']")
        assert result.submitted is False, f"{name} submitted in dry_run"
        assert result.dry_run_stopped is True, f"{name} missing dry_run_stopped"
        assert page.click_count == 0, f"{name} clicked submit ({page.click_count})"
        clicks_via_patch["n"] += page.click_count

    assert clicks_via_patch["n"] == 0
    assert len(APPLIERS) >= 8
