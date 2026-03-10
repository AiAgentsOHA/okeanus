"""Argovis adapter — Argo float profile data.

~4,000 autonomous profiling floats measuring temperature, salinity,
and BGC parameters in the upper 2000m of the global ocean.

API docs: https://argovis-api.colorado.edu/docs/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://argovis-api.colorado.edu"


class ArgovisAdapter(BaseAdapter):
    """Connector for the Argovis Argo profile API (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "argovis"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "near-real-time"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch Argo float profiles within bbox and time range."""
        w, s, e, n = bbox

        # Argovis uses polygon as [[lon,lat],[lon,lat],...] closed ring
        polygon = f"[[{w},{s}],[{e},{s}],[{e},{n}],[{w},{n}],[{w},{s}]]"

        api_params: dict[str, Any] = {
            "polygon": polygon,
            "startDate": time_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endDate": time_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "compression": "minimal",
        }
        if source := params.get("source"):
            api_params["source"] = source

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/argo", params=api_params,
            )
            profiles = resp.json()
        except Exception as exc:
            logger.error("Argovis fetch failed: %s", exc)
            return []

        if not isinstance(profiles, list):
            return []

        observations: list[dict[str, Any]] = []

        for profile in profiles:
            # Minimal compression returns arrays:
            # [id, lon, lat, timestamp, sources, data_keys]
            if isinstance(profile, list):
                if len(profile) < 4:
                    continue
                profile_id = str(profile[0])
                lon = float(profile[1])
                lat = float(profile[2])
                date_str = str(profile[3])
                sources = profile[4] if len(profile) > 4 else []
                payload: dict[str, Any] = {"sources": sources}
            elif isinstance(profile, dict):
                geo = profile.get("geolocation", {})
                coords = geo.get("coordinates", [])
                if len(coords) < 2:
                    continue
                lon, lat = coords[0], coords[1]
                date_str = profile.get("timestamp") or ""
                profile_id = str(profile.get("_id", ""))
                payload = {
                    "platform_number": profile.get("platform_number", ""),
                    "cycle_number": profile.get("cycle_number"),
                }
            else:
                continue

            try:
                ts = datetime.fromisoformat(
                    date_str.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                continue

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"argo-{profile_id}",
                "source_name": "Argo Float Network",
                "quality_score": None,
                "payload": payload,
            })

        logger.info("Argovis returned %d profiles", len(observations))
        return observations
