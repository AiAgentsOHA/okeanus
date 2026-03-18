"""ILO ILOSTAT adapter — maritime employment statistics.

Employment data for fishing, aquaculture, maritime transport,
and shipbuilding sectors across 189 countries.

API: REST JSON at rplumber.ilo.org (columnar format).
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://rplumber.ilo.org/data/indicator/"

# Key maritime employment indicators (append _A for annual frequency)
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
            limit: max records (default: 500)
        """
        indicator = params.get("indicator", "EMP_TEMP_SEX_EC2_NB")
        country = params.get("country", "")
        isic_code = params.get("isic", "A03")
        limit = params.get("limit", 500)
        year_start = time_start.year
        year_end = time_end.year

        # rplumber.ilo.org API uses indicator_id with _A suffix for annual
        indicator_id = f"{indicator}_A"

        query: dict[str, Any] = {
            "id": indicator_id,
            "timefrom": str(year_start),
            "timeto": str(year_end),
            "format": "json",
        }
        if country:
            query["ref_area"] = country.upper()

        try:
            resp = await self._request("GET", BASE_URL, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("ILO fetch %s failed: %s", indicator, exc)
            return []

        if not isinstance(data, dict):
            logger.warning("ILO %s: unexpected response type %s", indicator, type(data).__name__)
            return []

        # Response is columnar: parallel arrays for each field
        ref_areas = data.get("ref_area", [])
        times = data.get("time", [])
        values = data.get("obs_value", [])
        classif1s = data.get("classif1", [])
        sexes = data.get("sex", [])

        n_records = len(values)
        if n_records == 0:
            return []

        observations: list[dict[str, Any]] = []

        # Filter to maritime ISIC codes
        isic_filter = f"EC2_ISIC4_{isic_code}" if not isic_code.startswith("EC2_") else isic_code

        for i in range(n_records):
            if len(observations) >= limit:
                break

            # Filter by ISIC classification if classif1 is available
            classif = classif1s[i] if i < len(classif1s) else ""
            if classif and isic_filter and isic_filter not in str(classif):
                continue

            # Filter by sex = total (SEX_T)
            sex = sexes[i] if i < len(sexes) else ""
            if sex and sex != "SEX_T":
                continue

            ref_area_val = ref_areas[i] if i < len(ref_areas) else ""
            time_val = times[i] if i < len(times) else ""
            obs_value = values[i] if i < len(values) else None

            if obs_value is None:
                continue

            try:
                yr = int(str(time_val)[:4])
                ts = datetime(yr, 1, 1)
                val = float(obs_value)
            except (ValueError, TypeError):
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
                    "value": val,
                    "sex": "Total",
                },
            })

        logger.info("ILO ILOSTAT returned %d observations", len(observations))
        return observations
