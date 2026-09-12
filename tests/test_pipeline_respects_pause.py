"""Paused automation must not start a new pipeline run."""

from __future__ import annotations

from core.config import empty_app_config
from app.main import run_pipeline


def test_run_pipeline_returns_paused_without_search(tmp_path, monkeypatch):
    cfg = empty_app_config(root=tmp_path)
    cfg.settings.automation_paused = True
    called = {"n": 0}

    def boom(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("search must not run while paused")

    monkeypatch.setattr("app.main.build_sources", boom)
    stats = run_pipeline(cfg)
    assert stats.get("paused") is True or stats.get("cancelled") is True
    assert called["n"] == 0
