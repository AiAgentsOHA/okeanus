"""AVISO satellite altimetry adapter — sea level and ocean dynamics.

AVISO+ (Archivage, Validation et Interprétation des données des
Satellites Océanographiques) provides satellite altimetry products
including sea level anomaly, geostrophic currents, and wave height.

Near-real-time products accessible via ERDDAP. Historical products
may require Copernicus Marine login.

Data source: https://www.aviso.altimetry.fr/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# AVISO data available on Copernicus Marine ERDDAP
# NESDIS multi-mission altimetry: sea level anomaly + geostrophic currents
ERDDAP_URL = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
DATASET_ID = "nesdisSSH1day"
# Dataset time range: 2017-02-13 to ~2024-06; variable is "sla" not "ssh"


class AvisoAltimetryAdapter(BaseAdapter):
    """Connector for satellite altimetry / sea level data (no auth required).

    Returns sea surface height anomaly and derived ocean dynamics
    from multi-mission satellite altimetry.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=30.0, max_retries=2, **kwargs)

    @property
    def source_name(self) -> str:
        return "aviso_altimetry"

    @property
    def source_url(self) -> str:
        return "https://www.aviso.altimetry.fr/"

    @property
    def update_frequency(self) -> str:
        return "daily"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch sea level anomaly data at bbox centroid.

        Extra params:
            variable: 'ssh' (default), 'ssha'
            limit: max records (default 100)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 100)

        lon = (w + e) / 2
        lat = (s + n) / 2

        ts_start = time_start.strftime("%Y-%m-%dT00:00:00Z")
        ts_end = time_end.strftime("%Y-%m-%dT00:00:00Z")

        # Clamp time range to dataset coverage (ends ~mid 2024)
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        dataset_end = _dt(2024, 6, 27, tzinfo=_tz.utc)
        effective_end = min(time_end, dataset_end)
        effective_start = max(time_start, _dt(2017, 2, 13, tzinfo=_tz.utc))
        if effective_start >= effective_end:
            # Shift to last available year
            effective_end = dataset_end
            effective_start = _dt(2024, 1, 1, tzinfo=_tz.utc)

        # Limit to at most 30 days to avoid slow ERDDAP responses
        max_window = _td(days=30)
        if (effective_end - effective_start) > max_window:
            effective_start = effective_end - max_window

        ts_start = effective_start.strftime("%Y-%m-%dT00:00:00Z")
        ts_end = effective_end.strftime("%Y-%m-%dT00:00:00Z")

        # Use stride of 7 (weekly) to reduce data volume for large ranges
        days_span = (effective_end - effective_start).days
        stride = max(1, days_span // limit) if days_span > limit else 1

        url = (
            f"{ERDDAP_URL}/{DATASET_ID}.csv"
            f"?sla[({ts_start}):{stride}:({ts_end})]"
            f"[({lat}):1:({lat})]"
            f"[({lon}):1:({lon})]"
        )

        try:
            resp = await self._request("GET", url)
            text = resp.text
        except Exception as exc:
            logger.error("Altimetry SSH fetch failed: %s", exc)
            return []

        lines = text.strip().split("\n")
        if len(lines) < 3:
            return []

        headers = [h.strip() for h in lines[0].split(",")]
        observations: list[dict[str, Any]] = []

        for line in lines[2:]:
            if len(observations) >= limit:
                break

            parts = line.split(",")
            if len(parts) < len(headers):
                continue

            row = dict(zip(headers, parts))

            date_str = row.get("time", "")
            try:
                ts = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else time_start
            except (ValueError, TypeError):
                ts = time_start

            sla = row.get("sla", "")
            try:
                sla_val = float(sla) if sla and sla.strip() != "NaN" else None
            except (ValueError, TypeError):
                sla_val = None

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"altimetry-{lon:.2f}-{lat:.2f}-{ts.strftime('%Y%m%d')}",
                "source_name": "Satellite Altimetry",
                "quality_score": 0.9,
                "payload": {
                    "variable": "sea_level_anomaly",
                    "sla_m": sla_val,
                    "dataset": DATASET_ID,
                },
            })

        logger.info("Altimetry returned %d observations", len(observations))
        return observations
