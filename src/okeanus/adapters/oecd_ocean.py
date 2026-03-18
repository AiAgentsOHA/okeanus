"""OECD Ocean Economy Database adapter.

Ocean-based industries value-added, employment, and innovation metrics
across 140+ countries and 25+ years.

API: SDMX REST 3.0 at sdmx.oecd.org.
No auth required.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://sdmx.oecd.org/public/rest/data"

# Key OECD ocean/maritime datasets — maps short name to (DSD, DF) tuple
# Correct dataflow IDs discovered from sdmx.oecd.org/public/rest/dataflow/OECD.TAD.ARP
DATASETS = {
    "FISH_AQUA": "Aquaculture production",
    "FISH_EMPL": "Fisheries employment",
    "FISH_FLEET": "Fishing fleet",
    "FSE": "Fisheries support estimate",
}

# Map dataset short names to their actual SDMX 3.0 dataflow paths
_DATAFLOW_MAP = {
    "FISH_AQUA": "OECD.TAD.ARP,DSD_FISH_PROD@DF_FISH_AQUA",
    "FISH_EMPL": "OECD.TAD.ARP,DSD_FISH_EMP@DF_FISH_EMPL",
    "FISH_FLEET": "OECD.TAD.ARP,DSD_FISH_FLEET@DF_FISH_FLEET",
    "FSE": "OECD.TAD.ARP,DSD_FISH_FSE@DF_FSE",
}


class OecdOceanAdapter(BaseAdapter):
    """Connector for OECD SDMX 3.0 API — ocean economy data (no auth).

    Returns fisheries, maritime transport, and ocean-industry statistics
    for OECD and partner countries.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "oecd_ocean"

    @property
    def source_url(self) -> str:
        return "https://sdmx.oecd.org/"

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
        """Fetch OECD ocean economy statistics.

        Extra params:
            dataset: OECD dataset code (default: FISH_AQUA)
            country: ISO3 code (e.g. 'NOR', 'JPN') or 'all'
            limit: max records (default: 500)
        """
        dataset = params.get("dataset", "FISH_AQUA")
        country = params.get("country", "")
        limit = params.get("limit", 500)
        year_start = time_start.year
        year_end = time_end.year
        # OECD fisheries data has 1-2 year publication lag; widen range
        if year_end - year_start < 3:
            year_start = year_end - 5

        # Look up the correct dataflow path
        dataflow = _DATAFLOW_MAP.get(dataset)
        if not dataflow:
            logger.error("OECD: unknown dataset %s, valid: %s", dataset, list(_DATAFLOW_MAP))
            return []

        # SDMX 3.0 URL: /data/{agencyID},{datastructureID},{version}/{key}
        key = "all"
        url = f"{BASE_URL}/{dataflow}/{key}"

        query: dict[str, Any] = {
            "startPeriod": str(year_start),
            "endPeriod": str(year_end),
            "dimensionAtObservation": "AllDimensions",
        }

        try:
            resp = await self._request("GET", url, params=query)
            xml_text = resp.text
        except Exception as exc:
            logger.error("OECD SDMX 3.0 fetch %s failed: %s", dataset, exc)
            return []

        return self._parse_generic_data_xml(xml_text, dataset, country, limit)

    def _parse_generic_data_xml(
        self,
        xml_text: str,
        dataset: str,
        country_filter: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Parse SDMX GenericData XML response from OECD."""
        observations: list[dict[str, Any]] = []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.error("OECD XML parse error: %s", exc)
            return []

        # Handle namespaces — find all Obs elements regardless of namespace
        # SDMX generic format uses: generic:Obs with ObsKey/ObsValue
        ns_map: dict[str, str] = {}
        for event, elem in ET.iterparse(__import__("io").StringIO(xml_text), events=["start-ns"]):
            prefix, uri = elem
            if prefix:
                ns_map[prefix] = uri

        generic_ns = ns_map.get("generic", "")
        message_ns = ns_map.get("message", "")

        # Build namespace-aware tag names
        def ns_tag(ns: str, tag: str) -> str:
            return f"{{{ns}}}{tag}" if ns else tag

        obs_tag = ns_tag(generic_ns, "Obs")
        obs_key_tag = ns_tag(generic_ns, "ObsKey")
        obs_value_tag = ns_tag(generic_ns, "ObsValue")
        value_tag = ns_tag(generic_ns, "Value")

        for obs_elem in root.iter(obs_tag):
            if len(observations) >= limit:
                break

            # Extract dimension values from ObsKey
            dims: dict[str, str] = {}
            obs_key_elem = obs_elem.find(obs_key_tag)
            if obs_key_elem is not None:
                for val_elem in obs_key_elem.findall(value_tag):
                    dim_id = val_elem.get("id", "")
                    dim_val = val_elem.get("value", "")
                    dims[dim_id] = dim_val

            # Extract observation value
            obs_value_elem = obs_elem.find(obs_value_tag)
            if obs_value_elem is None:
                continue
            raw_value = obs_value_elem.get("value", "")
            if not raw_value:
                continue

            try:
                val_f = float(raw_value)
            except (ValueError, TypeError):
                continue

            ref_area = dims.get("REF_AREA", "")
            time_period = dims.get("TIME_PERIOD", "")
            measure = dims.get("MEASURE", "")
            species = dims.get("SPECIES", "")
            unit = dims.get("UNIT_MEASURE", "")

            # Apply country filter
            if country_filter and ref_area != country_filter.upper():
                continue

            try:
                yr = int(time_period[:4])
                ts = datetime(yr, 1, 1)
            except (ValueError, TypeError):
                continue

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"oecd-{dataset}-{ref_area}-{species}-{time_period}",
                "source_name": "OECD",
                "quality_score": 0.95,
                "payload": {
                    "dataset": dataset,
                    "dataset_name": DATASETS.get(dataset, dataset),
                    "country": ref_area,
                    "year": yr,
                    "measure": measure,
                    "species": species,
                    "unit": unit,
                    "value": val_f,
                },
            })

        logger.info("OECD %s returned %d observations", dataset, len(observations))
        return observations
