"""Hard guard: _maybe_submit must never click submit in dry_run / non-submit mode."""

from __future__ import annotations

from apply.base import BaseApplier


class _DummyApplier(BaseApplier):
    def _do_apply(self, job, resume_pdf_path, cover_letter_text, profile):
        raise NotImplementedError


class _ClickTrackingPage:
    def __init__(self) -> None:
        self.clicked = False

    def wait_for_selector(self, *args, **kwargs):
        return object()

    def query_selector(self, *args, **kwargs):
        page = self

        class _Btn:
            def is_visible(self) -> bool:
                return True

            def click(self) -> None:
                page.clicked = True

        return _Btn()


def test_maybe_submit_never_submits_when_dry_run():
    page = _ClickTrackingPage()
    applier = _DummyApplier(page, dry_run=True, submit=True)
    result = applier._maybe_submit("button[type='submit']")
    assert result.dry_run_stopped is True
    assert result.submitted is False
    assert page.clicked is False


def test_maybe_submit_never_submits_when_submit_false():
    page = _ClickTrackingPage()
    applier = _DummyApplier(page, dry_run=False, submit=False)
    result = applier._maybe_submit("button[type='submit']")
    assert result.dry_run_stopped is True
    assert result.submitted is False
    assert page.clicked is False
