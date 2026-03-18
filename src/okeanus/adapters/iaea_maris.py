"""IAEA MARIS (Marine Radioactivity Information System) adapter.

MARIS is the IAEA's global database of marine radioactivity
measurements -- radionuclide concentrations in seawater, sediment,
and biota from 1960-present (432 000+ sample points).

The MARIS website (maris.iaea.org) is an Angular SPA whose backend
exposes a JSON POST API.  The server uses a non-standard TLS cipher
suite, so we create a custom SSL context with SECLEVEL=1.

Data source: https://maris.iaea.org/
"""

from __future__ import annotations

import logging
import ssl
from datetime import datetime
from typing import Any

import httpx

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# MARIS Angular SPA backend API (discovered via JS bundle analysis)
SAMPLE_DATA_URL = "https://maris.iaea.org/api/Search/getsampledata"
DETAIL_URL = "https://maris.iaea.org/api/Search/getSampleDetails"


def _maris_ssl_context() -> ssl.SSLContext:
    """Return an SSL context compatible with the MARIS server's cipher suite."""
    ctx = ssl.create_default_context()
    ctx.set_ciphers("DEFAULT@SECLEVEL=1")
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class IaeaMarisAdapter(BaseAdapter):
    """Connector for IAEA MARIS marine radioactivity data (no auth required).

    Returns sample-level records (location + measurement count) from the
    global MARIS database.  The API returns all samples in a single
    response (~430 K records, ~10 MB) so results are filtered client-side
    by bounding box and capped by *limit*.

    Note: The MARIS server requires a reduced TLS security level.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=0.5, timeout=90.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "iaea_maris"

    @property
    def source_url(self) -> str:
        return "https://maris.iaea.org/"

    @property
    def update_frequency(self) -> str:
        return "yearly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch MARIS marine radioactivity sample locations.

        Extra params:
            sample_type: 0=all, 1=seawater, 2=biota, 3=sediment (default 0)
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        sample_type = params.get("sample_type", 0)

        body: dict[str, Any] = {
            "bioGroups": [],
            "sampleTypeId": int(sample_type),
            "shapeTypeId": 1,
        }

        ssl_ctx = _maris_ssl_context()

        try:
            async with httpx.AsyncClient(
                verify=ssl_ctx, timeout=self._timeout, follow_redirects=True,
            ) as client:
                resp = await client.post(
                    SAMPLE_DATA_URL,
                    json=body,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                resp.raise_for_status()
                records = resp.json()
        except Exception as exc:
            logger.error("IAEA MARIS fetch failed: %s", exc)
            return []

        if not isinstance(records, list):
            logger.warning("IAEA MARIS unexpected response type: %s", type(records))
            return []

        _sample_type_label = {0: "all", 1: "seawater", 2: "biota", 3: "sediment", 4: "suspended_matter"}

        observations: list[dict[str, Any]] = []
        for rec in records:
            if len(observations) >= limit:
                break

            pos = rec.get("pos", "")
            if not pos or "," not in pos:
                continue

            try:
                # MARIS pos format is "lon,lat" (longitude first)
                lon_str, lat_str = pos.split(",", 1)
                lon_f = float(lon_str)
                lat_f = float(lat_str)
            except (ValueError, TypeError):
                continue

            # Spatial filter
            if not (w <= lon_f <= e and s <= lat_f <= n):
                continue

            observations.append({
                "obs_type": "physical",
                "timestamp": time_start,  # MARIS summary doesn't include per-sample dates
                "geometry": {"type": "Point", "coordinates": [lon_f, lat_f]},
                "source_id": f"maris-{rec.get('id', len(observations))}",
                "source_name": "IAEA MARIS",
                "quality_score": 0.9,
                "payload": {
                    "sample_id": rec.get("id"),
                    "measurement_count": rec.get("measureCount", 0),
                    "sample_type": _sample_type_label.get(sample_type, "unknown"),
                    "position_raw": pos,
                },
            })

        logger.info("IAEA MARIS returned %d samples", len(observations))
        return observations
