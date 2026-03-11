"""ILO ILOSTAT adapter — maritime employment statistics.

Employment data for fishing, aquaculture, maritime transport,
and shipbuilding sectors across 189 countries.

API: SDMX REST at ilostat.ilo.org.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ilo.org/sdmx/rest/data"

# Key maritime employment indicators
INDICATORS = {
    "EMP_TEMP_SEX_EC2_NB": "Employment by economic activity (ISIC Rev.4)",
    "EAR_XEES_SEX_EC2_NB": "Mean monthly earnings by economic activity",
    "INJ_FATL_SEX_EC2_NB": "Fatal occupational injuries by activity",
    "TRU_DEMP_SEX_EC2_NB": "Trade union density by activity",
}

# ISIC Rev.4 codes for maritime sectors
MARITIME_ISIC = {
    "A03": "Fishing and aquaculture",
    "C102": "Processing of fish, crustaceans, molluscs",
    "H50": "Water transport",
    "C301": "Building of ships and boats",
}


class IloMaritimeAdapter(BaseAdapter):
    """Connector for ILO ILOSTAT — maritime employment (no auth required).

    Returns employment, earnings, and occupational safety data for
    fishing, water transport, and shipbuilding sectors.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ilo_maritime"

    @property
    def source_url(self) -> str:
        return "https://ilostat.ilo.org/"

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
        """Fetch ILO maritime employment statistics.

        Extra params:
            indicator: ILOSTAT indicator ID (default: EMP_TEMP_SEX_EC2_NB)
            country: ISO3 code (e.g. 'USA', 'NOR')
            isic: ISIC Rev.4 code for sector (default: A03 = fishing)
        """
        indicator = params.get("indicator", "EMP_TEMP_SEX_EC2_NB")
        country = params.get("country", "")
        isic_code = params.get("isic", "A03")
        year_start = time_start.year
        year_end = time_end.year

        # Build SDMX key: freq.ref_area.source.sex.classif1.classif2
        ref_area = country.upper() if country else ""
        key = f"A.{ref_area}..T.EC2_{isic_code}."

        url = f"{BASE_URL}/ILO,DF_{indicator}/{key}"
        query: dict[str, Any] = {
            "startPeriod": str(year_start),
            "endPeriod": str(year_end),
            "format": "jsondata",
            "detail": "dataonly",
        }

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("ILO fetch %s failed: %s", indicator, exc)
            return []

        observations: list[dict[str, Any]] = []

        datasets = data.get("dataSets", [])
        structure = data.get("structure", {})
        dims = structure.get("dimensions", {}).get("series", [])
        obs_dims = structure.get("dimensions", {}).get("observation", [])

        # Map dimension indices to labels
        dim_labels = {}
        for dim in dims:
            dim_id = dim.get("id", "")
            values = dim.get("values", [])
            dim_labels[dim_id] = {str(i): v.get("name", v.get("id", "")) for i, v in enumerate(values)}

        # Time periods from observation dimension
        time_values = {}
        for dim in obs_dims:
            if dim.get("id") == "TIME_PERIOD":
                for i, v in enumerate(dim.get("values", [])):
                    time_values[str(i)] = v.get("id", v.get("name", ""))

        if not datasets:
            return []

        series = datasets[0].get("series", {})
        for series_key, series_val in series.items():
            # Parse series key to extract dimension values
            key_parts = series_key.split(":")
            ref_area_val = ""
            for dim, idx in zip(dims, key_parts):
                if dim.get("id") == "REF_AREA":
                    values = dim.get("values", [])
                    try:
                        ref_area_val = values[int(idx)].get("id", "")
                    except (IndexError, ValueError):
                        pass

            for obs_key, obs_val in series_val.get("observations", {}).items():
                if not obs_val:
                    continue

                period = time_values.get(obs_key, "")
                try:
                    yr = int(period[:4])
                    ts = datetime(yr, 1, 1)
                    value = float(obs_val[0]) if isinstance(obs_val, list) else float(obs_val)
                except (ValueError, TypeError, IndexError):
                    continue

                observations.append({
                    "obs_type": "economic",
                    "timestamp": ts,
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "source_id": f"ilo-{indicator}-{ref_area_val}-{isic_code}-{yr}",
                    "source_name": "ILO ILOSTAT",
                    "quality_score": 0.90,
                    "payload": {
                        "indicator": indicator,
                        "country": ref_area_val,
                        "isic_code": isic_code,
                        "sector_name": MARITIME_ISIC.get(isic_code, isic_code),
                        "year": yr,
                        "value": value,
                        "sex": "Total",
                    },
                })

        logger.info("ILO ILOSTAT returned %d observations", len(observations))
        return observations
