"""Job source base interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from core.models import Job


@dataclass
class SearchQuery:
    keyword: str
    location: str = ""
    radius_km: float = 20
    max_results: int = 50
    published_within_days: int = 14
    extra: dict[str, Any] = field(default_factory=dict)


class JobSource(ABC):
    source_id: str = "base"

    @abstractmethod
    def search(self, queries: list[SearchQuery]) -> list[Job]:
        """Return normalized Job objects. Must not raise for empty results."""

    def safe_search(self, queries: list[SearchQuery]) -> tuple[list[Job], str | None]:
        try:
            return self.search(queries), None
        except Exception as exc:  # noqa: BLE001 — isolate source failures
            return [], str(exc)
