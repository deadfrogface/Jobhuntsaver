"""Optional helpers for scheduled one-shot runs."""

from __future__ import annotations

from app.main import run_pipeline
from core.config import load_config


def run_once() -> dict:
    """Start → process → exit. Designed for Windows Task Scheduler."""
    return run_pipeline(load_config())
