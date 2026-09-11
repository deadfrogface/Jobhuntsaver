"""Remote/hybrid allow flags must apply even within radius."""

from __future__ import annotations

from core.config import empty_app_config
from core.hard_filter import hard_exclude
from core.models import Job, RemoteType


def _cfg(*, allow_remote=True, allow_hybrid=True, max_km=20.0):
    cfg = empty_app_config()
    cfg.profile.location.max_distance_km = max_km
    cfg.profile.location.allow_remote_germany = allow_remote
    cfg.profile.location.allow_hybrid = allow_hybrid
    return cfg


def _job(*, remote: str, distance: float | None = 5.0) -> Job:
    return Job(
        id="j1",
        source="test",
        title="Sachbearbeiter",
        company="ACME",
        description="",
        city="Berlin",
        distance_km=distance,
        remote_type=remote,
        url="https://example.com/1",
    )


def test_nearby_hybrid_blocked_when_hybrid_disallowed():
    reason = hard_exclude(_job(remote=RemoteType.HYBRID.value, distance=5.0), _cfg(allow_hybrid=False))
    assert reason is not None
    assert "hybrid" in reason.lower()


def test_nearby_remote_blocked_when_remote_disallowed():
    reason = hard_exclude(_job(remote=RemoteType.REMOTE.value, distance=5.0), _cfg(allow_remote=False))
    assert reason is not None
    assert "remote" in reason.lower()


def test_far_remote_allowed_when_remote_enabled():
    assert hard_exclude(_job(remote=RemoteType.REMOTE.value, distance=500.0), _cfg(allow_remote=True)) is None
