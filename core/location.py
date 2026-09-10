"""Geocoding cache and Haversine distance helpers.

Nominatim calls are rate-limited, timed out, negatively cached, and must never
block a search run indefinitely.

Home coordinates are resolved **once per LocationService instance / run**.
Failed home resolution must NOT silently use arbitrary Germany center coordinates
for distance filtering — that distorts commute filters.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

import httpx

if TYPE_CHECKING:
    from core.config import AppConfig
    from core.database import Database

logger = logging.getLogger("jobhuntsaver")

# Sentinel display_name for failed lookups (persisted so we do not retry forever).
UNRESOLVED_MARKER = "__unresolved__"
DEFAULT_GEOCODE_TIMEOUT_S = 5.0
MIN_REQUEST_INTERVAL_S = 1.05
# Negative-cache TTL for unresolved lookups (seconds). Successes stay until cleared.
UNRESOLVED_TTL_S = 6 * 60 * 60
# Soft cap on unique geocode network attempts per enrich run (cached hits free).
MAX_UNIQUE_GEOCODE_ATTEMPTS_PER_RUN = 80


@dataclass
class HomeResolution:
    """Outcome of resolving the search-origin / home coordinates."""

    coords: tuple[float, float] | None = None
    resolved: bool = False
    source: str = ""  # persisted | geocode | unresolved
    warning: str = ""
    address_used: str = ""


@dataclass
class EnrichStats:
    total: int = 0
    remote_skipped: int = 0
    resolved: int = 0
    cached: int = 0
    failed: int = 0
    unique_queries: int = 0
    home_resolved: bool = False
    home_warning: str = ""
    skipped_distance_no_home: bool = False


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


def location_cache_key(
    *,
    address: str = "",
    city: str = "",
    postal_code: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
) -> str:
    """Stable key for deduplicating geocode work within a run."""
    if latitude is not None and longitude is not None:
        return f"ll:{latitude:.5f},{longitude:.5f}"
    parts = [p.strip().lower() for p in (address, postal_code, city) if p and str(p).strip()]
    if not parts:
        return ""
    return "|".join(parts)


@dataclass
class LocationService:
    """Geocode once, cache in SQLite (incl. misses), compute Haversine locally."""

    db: "Database"
    config: "AppConfig"
    timeout_s: float = DEFAULT_GEOCODE_TIMEOUT_S
    _home: tuple[float, float] | None = field(default=None, init=False, repr=False)
    _home_resolution: HomeResolution | None = field(default=None, init=False, repr=False)
    _last_request: float = field(default=0.0, init=False, repr=False)
    _memory_hits: dict[str, tuple[float, float, str] | None] = field(
        default_factory=dict, init=False, repr=False
    )
    _network_attempts: int = field(default=0, init=False, repr=False)
    home_updated: bool = field(default=False, init=False, repr=False)
    stats: EnrichStats = field(default_factory=EnrichStats, init=False)

    @property
    def home_resolved(self) -> bool:
        res = self._home_resolution
        return bool(res and res.resolved and res.coords)

    @property
    def home_warning(self) -> str:
        res = self._home_resolution
        return (res.warning if res else "") or ""

    def resolve_home(self) -> HomeResolution:
        """Resolve home once. Never uses a silent Germany-center fallback for filtering."""
        if self._home_resolution is not None:
            return self._home_resolution

        loc = self.config.profile.location
        address = (loc.home_address or "").strip()

        if loc.home_latitude is not None and loc.home_longitude is not None:
            coords = (float(loc.home_latitude), float(loc.home_longitude))
            self._home = coords
            self._home_resolution = HomeResolution(
                coords=coords,
                resolved=True,
                source="persisted",
                address_used=address,
            )
            self.stats.home_resolved = True
            return self._home_resolution

        if not address:
            warning = (
                "Such-Standort fehlt: bitte eine Heimatadresse unter Profil/Standort setzen. "
                "Distanzfilter ist deaktiviert, bis der Standort auflösbar ist."
            )
            logger.warning(warning)
            self._home_resolution = HomeResolution(
                coords=None,
                resolved=False,
                source="unresolved",
                warning=warning,
                address_used="",
            )
            self.stats.home_resolved = False
            self.stats.home_warning = warning
            self.stats.skipped_distance_no_home = True
            return self._home_resolution

        coords_t = self.geocode(address)
        if not coords_t:
            cityish = _city_from_address(address)
            if cityish and cityish.lower() != address.lower():
                coords_t = self.geocode(f"{cityish}, Germany")

        if not coords_t:
            warning = (
                f"Heimatadresse konnte nicht geocodiert werden: {address!r}. "
                "Distanzfilter übersprungen — bitte Adresse korrigieren (kein generischer DE-Fallback)."
            )
            logger.warning(warning)
            self._home = None
            self._home_resolution = HomeResolution(
                coords=None,
                resolved=False,
                source="unresolved",
                warning=warning,
                address_used=address,
            )
            self.stats.home_resolved = False
            self.stats.home_warning = warning
            self.stats.skipped_distance_no_home = True
            return self._home_resolution

        coords = (coords_t[0], coords_t[1])
        self._home = coords
        loc.home_latitude = coords[0]
        loc.home_longitude = coords[1]
        self.home_updated = True
        self._home_resolution = HomeResolution(
            coords=coords,
            resolved=True,
            source="geocode",
            address_used=address,
        )
        self.stats.home_resolved = True
        return self._home_resolution

    def ensure_home_coords(self) -> tuple[float, float] | None:
        """Resolve home once; return coords or None if unresolved (no DE fallback)."""
        res = self.resolve_home()
        return res.coords

    def geocode(self, query: str) -> tuple[float, float, str] | None:
        query = (query or "").strip()
        if not query:
            return None
        key = query.lower()
        if key in self._memory_hits:
            self.stats.cached += 1
            return self._memory_hits[key]

        cached = self.db.get_geocode(query)
        if cached is not None:
            lat, lon, display, cached_at = cached
            if display == UNRESOLVED_MARKER:
                age = _age_seconds(cached_at)
                if age is not None and age < UNRESOLVED_TTL_S:
                    self._memory_hits[key] = None
                    self.stats.cached += 1
                    return None
                # TTL expired — allow one retry
            else:
                result = (lat, lon, display)
                self._memory_hits[key] = result
                self.stats.cached += 1
                return result

        if self._network_attempts >= MAX_UNIQUE_GEOCODE_ATTEMPTS_PER_RUN:
            logger.warning(
                "Geocode attempt cap (%s) reached — skipping %r",
                MAX_UNIQUE_GEOCODE_ATTEMPTS_PER_RUN,
                query,
            )
            self.stats.failed += 1
            return None

        elapsed = time.time() - self._last_request
        if elapsed < MIN_REQUEST_INTERVAL_S:
            time.sleep(MIN_REQUEST_INTERVAL_S - elapsed)

        self._network_attempts += 1
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                resp = client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1,
                        "countrycodes": (
                            self.config.profile.location.country or "DE"
                        ).lower(),
                    },
                    headers={"User-Agent": "Jobhuntsaver/1.0 (local personal use)"},
                )
                resp.raise_for_status()
                data = resp.json()
            self._last_request = time.time()
            if not data:
                self._store_unresolved(query)
                self.stats.failed += 1
                return None
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            display = data[0].get("display_name", "") or ""
            self.db.set_geocode(query, lat, lon, display)
            result = (lat, lon, display)
            self._memory_hits[key] = result
            self.stats.resolved += 1
            return result
        except Exception as exc:
            logger.warning("Geocode failed for %r: %s", query, exc)
            self._store_unresolved(query)
            self.stats.failed += 1
            return None

    def _store_unresolved(self, query: str) -> None:
        key = query.lower().strip()
        self._memory_hits[key] = None
        try:
            self.db.set_geocode(query, 0.0, 0.0, UNRESOLVED_MARKER)
        except Exception as exc:
            logger.debug("Could not persist unresolved geocode for %r: %s", query, exc)

    def distance_for_job_location(
        self,
        *,
        address: str = "",
        city: str = "",
        postal_code: str = "",
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> tuple[float | None, float | None, float | None]:
        """Return (lat, lon, distance_km). Unresolved home → no distance filter value."""
        home = self.ensure_home_coords()
        if home is None:
            # Still try to resolve job coords for map/display, but no distance.
            if latitude is not None and longitude is not None:
                return latitude, longitude, None
            query_parts = [p for p in (address, postal_code, city, "Germany") if p]
            query = ", ".join(query_parts) if any([address, city, postal_code]) else ""
            if not query:
                return None, None, None
            result = self.geocode(query)
            if not result and city:
                result = self.geocode(f"{city}, Germany")
            if not result and postal_code:
                result = self.geocode(f"{postal_code}, Germany")
            if not result:
                return None, None, None
            return result[0], result[1], None

        if latitude is not None and longitude is not None:
            return (
                latitude,
                longitude,
                round(haversine_km(home[0], home[1], latitude, longitude), 2),
            )

        query_parts = [p for p in (address, postal_code, city, "Germany") if p]
        query = ", ".join(query_parts) if any([address, city, postal_code]) else ""
        if not query:
            return None, None, None
        result = self.geocode(query)
        if not result and city:
            result = self.geocode(f"{city}, Germany")
        if not result and postal_code:
            result = self.geocode(f"{postal_code}, Germany")
        if not result:
            return None, None, None
        lat, lon, _ = result
        return lat, lon, round(haversine_km(home[0], home[1], lat, lon), 2)


def _age_seconds(cached_at: str | None) -> float | None:
    if not cached_at:
        return None
    try:
        # ISO timestamps from utc_now_iso
        from datetime import datetime, timezone

        text = str(cached_at).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds()
    except Exception:
        return None


def _city_from_address(home_address: str) -> str:
    parts = [p.strip() for p in home_address.split(",") if p.strip()]
    for part in reversed(parts):
        low = part.lower()
        if low in {"germany", "deutschland", "de"}:
            continue
        tokens = part.split()
        words = [t for t in tokens if not any(c.isdigit() for c in t)]
        if not words:
            continue
        if tokens and tokens[0].isdigit():
            return " ".join(words)
        if any(c.isdigit() for c in part):
            continue
        return " ".join(words)
    return ""


def enrich_job_locations(
    jobs: list,
    location: LocationService,
    *,
    progress_callback: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list:
    """Enrich jobs with coordinates/distance. Dedupes identical location queries.

    Remote jobs skip workplace geocoding. Progress reports unique-query progress.
    """

    def progress(msg: str) -> None:
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception:
                pass

    def stopped() -> bool:
        try:
            return bool(should_stop and should_stop())
        except Exception:
            return False

    location.stats = EnrichStats(total=len(jobs))
    home = location.resolve_home()
    if not home.resolved:
        progress(home.warning or "Heimatstandort unklar — Distanzfilter deaktiviert.")
        location.stats.home_resolved = False
        location.stats.home_warning = home.warning
        location.stats.skipped_distance_no_home = True
    else:
        location.stats.home_resolved = True

    groups: dict[str, list] = {}
    order: list[str] = []
    for job in jobs:
        if getattr(job, "remote_type", "") == "remote":
            job.distance_km = None
            location.stats.remote_skipped += 1
            continue
        key = location_cache_key(
            address=getattr(job, "address", "") or "",
            city=getattr(job, "city", "") or "",
            postal_code=getattr(job, "postal_code", "") or "",
            latitude=getattr(job, "latitude", None),
            longitude=getattr(job, "longitude", None),
        )
        if not key:
            continue
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(job)

    location.stats.unique_queries = len(order)
    total_q = max(len(order), 1)

    for idx, key in enumerate(order, start=1):
        if stopped():
            progress(f"Standorte anreichern abgebrochen ({idx - 1}/{len(order)}).")
            break
        group = groups[key]
        sample = group[0]
        progress(
            f"Standorte anreichern: {idx}/{len(order)} "
            f"(gelöst {location.stats.resolved}, Cache {location.stats.cached}, "
            f"offen {location.stats.failed})"
        )
        lat, lon, dist = location.distance_for_job_location(
            address=getattr(sample, "address", "") or "",
            city=getattr(sample, "city", "") or "",
            postal_code=getattr(sample, "postal_code", "") or "",
            latitude=getattr(sample, "latitude", None),
            longitude=getattr(sample, "longitude", None),
        )
        for job in group:
            if lat is not None:
                job.latitude = lat
                job.longitude = lon
            if dist is not None:
                job.distance_km = dist

    progress(
        f"Standorte fertig: {len(order)}/{total_q} Orte — "
        f"gelöst {location.stats.resolved}, Cache {location.stats.cached}, "
        f"ungeklärt {location.stats.failed}, Remote übersprungen {location.stats.remote_skipped}"
        + ("" if home.resolved else " | Distanzfilter inaktiv (Heimat unklar)")
    )
    return jobs
