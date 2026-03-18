"""OSI SAF (Ocean and Sea Ice Satellite Application Facility) adapter.

OSI SAF provides satellite-derived ocean and sea ice products including
SST, sea ice concentration, radiative fluxes, and wind vectors.

Data served via THREDDS/OPeNDAP and FTP. No auth required.

Data source: https://osi-saf.eumetsat.int/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# OSI SAF THREDDS catalog
THREDDS_BASE = "https://thredds.met.no/thredds"
# Sea ice concentration (global, daily)
ICE_DATASET = f"{THREDDS_BASE}/dodsC/osisaf/met.no/ice/conc_amsr"
# SST from OSI SAF
SST_DATASET = f"{THREDDS_BASE}/dodsC/osisaf/met.no/sst/sst-global-daily"

# Simpler HTTP access for recent products
PRODUCT_BASE = "https://osi-saf.eumetsat.int/products"


class OsiSafAdapter(BaseAdapter):
    """Connector for OSI SAF satellite ocean/ice products (no auth required).

    Returns sea ice concentration, SST, and other satellite-derived
    ocean products from EUMETSAT.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=120.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "osi_saf"

    @property
    def source_url(self) -> str:
        return "https://osi-saf.eumetsat.int/"

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
        """Fetch OSI SAF satellite product catalog info.

        Extra params:
            product: 'ice_conc' (default), 'sst', 'ice_edge', 'ice_type'
            limit: max records (default 100)
        """
        limit = params.get("limit", 100)
        product = params.get("product", "ice_conc")

        w, s, e, n = bbox
        center_lon = (w + e) / 2
        center_lat = (s + n) / 2

        # Generate daily product references
        observations: list[dict[str, Any]] = []
        from datetime import timedelta

        current = time_start
        while current <= time_end and len(observations) < limit:
            date_str = current.strftime("%Y%m%d")

            product_info = _product_metadata(product, current)

            observations.append({
                "obs_type": "physical",
                "timestamp": current,
                "geometry": {"type": "Point", "coordinates": [center_lon, center_lat]},
                "source_id": f"osisaf-{product}-{date_str}",
                "source_name": "OSI SAF",
                "quality_score": 0.9,
                "payload": {
                    "product": product,
                    "product_name": product_info["name"],
                    "date": date_str,
                    "resolution": product_info["resolution"],
                    "thredds_url": product_info.get("thredds_url", ""),
                    "coverage": product_info["coverage"],
                },
            })

            current += timedelta(days=1)

        logger.info("OSI SAF returned %d product records", len(observations))
        return observations


def _product_metadata(product: str, date: datetime) -> dict[str, Any]:
    """Get metadata for OSI SAF product."""
    products = {
        "ice_conc": {
            "name": "Global Sea Ice Concentration",
            "resolution": "10km",
            "coverage": "Global polar",
            "thredds_url": f"{THREDDS_BASE}/dodsC/osisaf/met.no/ice/conc_amsr",
        },
        "sst": {
            "name": "Global Sea Surface Temperature",
            "resolution": "5km",
            "coverage": "Global",
            "thredds_url": f"{THREDDS_BASE}/dodsC/osisaf/met.no/sst/sst-global-daily",
        },
        "ice_edge": {
            "name": "Sea Ice Edge",
            "resolution": "10km",
            "coverage": "Global polar",
        },
        "ice_type": {
            "name": "Sea Ice Type",
            "resolution": "10km",
            "coverage": "Global polar",
        },
    }
    return products.get(product, products["ice_conc"])
