"""Generic ERDDAP adapter — connects to any ERDDAP server.

ERDDAP is a standardized data server protocol used by hundreds of ocean
data providers (NOAA CoastWatch, IOOS, NDBC, PO.DAAC, etc.).

This adapter can query any ERDDAP tabledap or griddap endpoint.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Well-known ERDDAP servers
SERVERS = {
    # --- Original ---
    "coastwatch": "https://coastwatch.pfeg.noaa.gov/erddap",
    "ioos_gliders": "https://gliders.ioos.us/erddap",
    "osmc": "https://osmc.noaa.gov/erddap",
    "noaa_ncei": "https://www.ncei.noaa.gov/erddap",
    # --- NOAA Regional ---
    "pifsc_sst": "https://oceanwatch.pifsc.noaa.gov/erddap",
    "coops_tides": "https://opendap.co-ops.nos.noaa.gov/erddap",
    "polarwatch": "https://polarwatch.noaa.gov/erddap",
    "noaa_uaf": "https://upwell.pfeg.noaa.gov/erddap",
    "nefsc_shelf": "https://comet.nefsc.noaa.gov/erddap",
    "aoml_caribbean": "https://cwcgom.aoml.noaa.gov/erddap",
    # --- IOOS Regional Associations ---
    "ioos_sensors": "https://erddap.sensors.ioos.us/erddap",
    "cencoos": "http://erddap.cencoos.org/erddap",
    "nanoos": "https://erddap.nanoos.org/erddap",
    "aoos": "https://erddap.aoos.org/erddap",
    "pacioos": "https://pae-paha.pacioos.hawaii.edu/erddap",
    "gcoos": "https://erddap.gcoos.org/erddap",
    "secoora": "http://erddap.secoora.org/erddap",
    "neracoos": "https://data.neracoos.org/erddap",
    "atn_telemetry": "https://atn.ioos.us/erddap",
    # --- European ---
    "emodnet_physics": "https://erddap.emodnet-physics.eu/erddap",
    "emodnet_chemistry": "https://erddap.emodnet-chemistry.eu/erddap",
    "emodnet_unified": "https://erddap.emodnet.eu/erddap",
    "emso_seafloor": "http://erddap.emso.eu/erddap",
    "marine_institute_ie": "https://erddap.marine.ie/erddap",
    "bodc_uk": "https://linkedsystems.uk/erddap",
    # --- International ---
    "incois_india": "https://erddap.incois.gov.in/erddap",
    "ooi_cabled": "https://erddap.dataexplorer.oceanobservatories.org/erddap",
    # --- Specialized ---
    "apdrc_reanalysis": "https://apdrc.soest.hawaii.edu/erddap",
    "bco_dmo": "https://erddap.bco-dmo.org/erddap",
    "bio_oracle": "https://erddap.bio-oracle.org/erddap",
    "iode_oa": "https://erddap.oa.iode.org/erddap",
    "usgs_coastal": "https://geoport.usgs.esipfed.org/erddap",
    "hakai_bc": "https://catalogue.hakai.org/erddap",
    "spray_gliders": "https://spraydata.ucsd.edu/erddap",
}


class ErddapAdapter(BaseAdapter):
    """Generic connector for any ERDDAP tabledap endpoint."""

    def __init__(
        self,
        *,
        server_url: str = SERVERS["coastwatch"],
        dataset_id: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)
        self._server_url = server_url.rstrip("/")
        self._dataset_id = dataset_id

    @property
    def source_name(self) -> str:
        return "erddap"

    @property
    def source_url(self) -> str:
        return self._server_url

    @property
    def update_frequency(self) -> str:
        return "varies"

    async def list_datasets(self, search: str = "") -> list[dict[str, Any]]:
        """Search for datasets on this ERDDAP server."""
        url = f"{self._server_url}/search/index.json"
        params: dict[str, Any] = {"page": 1, "itemsPerPage": 50}
        if search:
            params["searchFor"] = search
        try:
            resp = await self._request("GET", url, params=params)
            data = resp.json()
            rows = data.get("table", {}).get("rows", [])
            col_names = data.get("table", {}).get("columnNames", [])
            return [dict(zip(col_names, row)) for row in rows]
        except Exception as exc:
            logger.error("ERDDAP dataset search failed: %s", exc)
            return []

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch data from an ERDDAP tabledap dataset with spatial/temporal filters."""
        dataset_id = params.get("dataset_id", self._dataset_id)
        if not dataset_id:
            logger.error("ERDDAP adapter requires dataset_id")
            return []

        server_url = params.get("server_url", self._server_url)
        variables = params.get("variables", "")
        obs_type = params.get("obs_type", "physical")

        w, s, e, n = bbox
        ts_start = time_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        ts_end = time_end.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Build ERDDAP constraint URL
        constraints = (
            f"&time>={ts_start}&time<={ts_end}"
            f"&latitude>={s}&latitude<={n}"
            f"&longitude>={w}&longitude<={e}"
        )
        limit = params.get("limit", 500)
        url = (
            f"{server_url}/tabledap/{dataset_id}.json"
            f"?{variables}{constraints}&orderByLimit(\"{limit}\")"
        )

        try:
            resp = await self._request("GET", url)
            data = resp.json()
        except Exception as exc:
            logger.error("ERDDAP fetch failed for %s: %s", dataset_id, exc)
            return []

        table = data.get("table", {})
        col_names = table.get("columnNames", [])
        rows = table.get("rows", [])

        observations: list[dict[str, Any]] = []
        time_idx = _find_col(col_names, "time")
        lat_idx = _find_col(col_names, "latitude")
        lon_idx = _find_col(col_names, "longitude")

        if time_idx is None or lat_idx is None or lon_idx is None:
            logger.warning("ERDDAP response missing time/lat/lon columns: %s", col_names)
            return []

        for i, row in enumerate(rows):
            try:
                ts_val = row[time_idx]
                ts = datetime.fromisoformat(str(ts_val).replace("Z", "+00:00"))
                lat = float(row[lat_idx])
                lon = float(row[lon_idx])
            except (ValueError, TypeError, IndexError):
                continue

            # Build payload from all other columns
            payload = {}
            for j, col in enumerate(col_names):
                if j not in (time_idx, lat_idx, lon_idx) and row[j] is not None:
                    payload[col] = row[j]

            observations.append({
                "obs_type": obs_type,
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"erddap-{dataset_id}-{i}",
                "source_name": f"ERDDAP:{dataset_id}",
                "quality_score": None,
                "payload": payload,
            })

        logger.info("ERDDAP returned %d rows from %s", len(observations), dataset_id)
        return observations


def _find_col(col_names: list[str], target: str) -> int | None:
    """Find column index by name (case-insensitive)."""
    target_l = target.lower()
    for i, name in enumerate(col_names):
        if name.lower() == target_l:
            return i
    return None
