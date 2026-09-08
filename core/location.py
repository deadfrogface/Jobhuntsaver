"""Geocoding cache and Haversine distance helpers."""

from __future__ import annotations

import logging
import math
import time
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from core.config import AppConfig
    from core.database import Database

logger = logging.getLogger("jobhuntsaver")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points in kilometres."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


class LocationService:
    """Geocode once, cache in SQLite, compute Haversine locally."""

    def __init__(self, db: "Database", config: "AppConfig") -> None:
        self.db = db
        self.config = config
        self._home: tuple[float, float] | None = None
        self._last_request = 0.0

    def ensure_home_coords(self) -> tuple[float, float]:
        loc = self.config.profile.location
        if loc.home_latitude is not None and loc.home_longitude is not None:
            self._home = (loc.home_latitude, loc.home_longitude)
            return self._home
        coords = self.geocode(loc.home_address)
        if not coords:
            # Approximate DE city-center fallback only if geocode fails
            logger.warning("Home geocode failed; using generic DE fallback coordinates")
            self._home = (51.1657, 10.4515)
            return self._home
        self._home = (coords[0], coords[1])
        return self._home

    def geocode(self, query: str) -> tuple[float, float, str] | None:
        query = (query or "").strip()
        if not query:
            return None
        cached = self.db.get_geocode(query)
        if cached:
            return cached
        # Respect Nominatim usage policy (~1 req/s)
        elapsed = time.time() - self._last_request
        if elapsed < 1.1:
            time.sleep(1.1 - elapsed)
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1,
                        "countrycodes": self.config.profile.location.country.lower(),
                    },
                    headers={"User-Agent": "Jobhuntsaver/1.0 (local personal use)"},
                )
                resp.raise_for_status()
                data = resp.json()
            self._last_request = time.time()
            if not data:
                return None
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            display = data[0].get("display_name", "")
            self.db.set_geocode(query, lat, lon, display)
            return lat, lon, display
        except Exception as exc:
            logger.warning("Geocode failed for '%s': %s", query, exc)
            return None

    def distance_for_job_location(
        self,
        *,
        address: str = "",
        city: str = "",
        postal_code: str = "",
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> tuple[float | None, float | None, float | None]:
        """Return (lat, lon, distance_km)."""
        home = self.ensure_home_coords()
        if latitude is not None and longitude is not None:
            return latitude, longitude, round(haversine_km(home[0], home[1], latitude, longitude), 2)

        query_parts = [p for p in (address, postal_code, city, "Germany") if p]
        query = ", ".join(query_parts) if any([address, city, postal_code]) else ""
        if not query:
            return None, None, None
        result = self.geocode(query)
        if not result:
            # Try city only
            if city:
                result = self.geocode(f"{city}, Germany")
        if not result:
            return None, None, None
        lat, lon, _ = result
        return lat, lon, round(haversine_km(home[0], home[1], lat, lon), 2)
