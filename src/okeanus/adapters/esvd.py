"""ESVD (Ecosystem Services Valuation Database) adapter.

Economic values ($/ha/year) for marine and coastal ecosystem services
including mangroves, coral reefs, seagrass, estuaries, open ocean.

Data: Database at https://esvd.net (export CSV).
Free registration required at https://esvd.info.

Primary mode: loads from a local CSV export placed in data/esvd/.
Fallback: attempts the ESVD REST API (requires registration token).

Citation:
  Brander, L.M. de Groot, R, et al. (2025). Ecosystem Services
  Valuation Database (ESVD). Foundation for Sustainable Development
  and Brander Environmental Economics. https://esvd.net
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://esvd.info/api/v1"

# Default directory for local CSV data (relative to project root)
_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "esvd"

# Marine/coastal ecosystem types
MARINE_BIOMES = {
    "coral_reef": "Coral reefs",
    "coral reefs": "Coral reefs",
    "mangrove": "Mangroves",
    "mangroves": "Mangroves",
    "seagrass": "Seagrass/algae beds",
    "seagrass/algae beds": "Seagrass/algae beds",
    "estuary": "Estuaries",
    "estuaries": "Estuaries",
    "coastal_wetland": "Coastal wetlands",
    "coastal wetlands": "Coastal wetlands",
    "salt_marsh": "Salt marshes",
    "salt marshes": "Salt marshes",
    "open_ocean": "Open ocean",
    "open ocean": "Open ocean",
    "continental_shelf": "Continental shelf",
    "continental shelf": "Continental shelf",
    "deep_sea": "Deep sea",
    "deep sea": "Deep sea",
    "coastal_systems": "Coastal systems (general)",
    "coastal systems": "Coastal systems (general)",
}

# Key ecosystem service categories
SERVICE_TYPES = {
    "provisioning": "Food, raw materials, genetic resources",
    "regulating": "Climate regulation, carbon sequestration, coastal protection",
    "habitat": "Nursery, biodiversity maintenance",
    "cultural": "Recreation, tourism, aesthetic",
}

# Flexible column-name mapping: canonical key -> list of possible CSV headers.
# The first match (case-insensitive) wins.
_COL_MAP: dict[str, list[str]] = {
    "value_id": ["ValueId", "Value ID", "value_id", "ValueID", "ID", "id"],
    "study_id": ["StudyId", "Study ID", "study_id", "StudyID"],
    "biome": ["ESVD2.0_Biome", "Biome", "biome", "Biome_name", "biome_name",
              "Ecosystem Type"],
    "biome_detail": ["ESVD2.0_Ecozones", "Biome Detail", "biome_detail", "Ecozone",
                     "Ecosystem Subtype"],
    "ecosystem_text": ["Ecosystem Text"],
    "service": ["ES_Text", "Ecosystem Service", "ecosystem_service", "ES", "Service",
                 "service", "Service Name", "serviceName"],
    "service_category": ["TEEB_ES", "ES Category", "es_category", "Service Category",
                         "service_category", "serviceType", "TEEB Category"],
    "service_sub": ["TEEB_SubES"],
    "method": ["Valuation Methods", "Valuation Method", "valuation_method",
               "Method", "method"],
    "value": ["Int$ Per Hectare Per Year", "Value (Int$/ha/yr)",
              "value_int_per_ha_yr", "Standardised Value",
              "standardised_value", "Value", "value", "Unit Value", "unitValue",
              "value_per_ha"],
    "value_original": ["Original Value", "Value (Original)", "value_original"],
    "currency": ["Currency", "Original Currency", "currency"],
    "country": ["Countries", "Country_1", "Country", "country"],
    "continent": ["Continent", "continent"],
    "latitude": ["Latitude", "latitude", "lat", "Lat"],
    "longitude": ["Longitude", "longitude", "lon", "Lon", "Long"],
    "study_year": ["Value Year", "Study Year", "study_year", "Year", "year",
                   "studyYear", "valuation_year"],
    "pub_year": ["Year_Pub", "Publication Year", "publication_year", "Pub Year"],
    "scale": ["Scale Of Site", "Scale", "scale"],
    "area_ha": ["Site Area In Hectares", "Area (ha)", "area_ha", "Area", "area"],
    "protected": ["Protection Status", "Protected Area", "protected_area", "Protected"],
    "reference": ["Reference", "reference", "Citation", "citation"],
}


def _resolve_columns(header: list[str]) -> dict[str, str | None]:
    """Build a mapping from canonical keys to actual CSV column names."""
    header_lower = {h.strip().lower(): h.strip() for h in header}
    resolved: dict[str, str | None] = {}
    for key, candidates in _COL_MAP.items():
        resolved[key] = None
        for cand in candidates:
            if cand.lower() in header_lower:
                resolved[key] = header_lower[cand.lower()]
                break
    return resolved


class EsvdAdapter(BaseAdapter):
    """Connector for ESVD -- ecosystem services $/ha values.

    Primary: reads from a local CSV export in ``data/esvd/``.
    Fallback: attempts the ESVD REST API (requires registration token).

    Returns economic valuations of marine and coastal ecosystem services
    from peer-reviewed studies worldwide.
    """

    def __init__(
        self,
        *,
        api_key: str = "",
        data_dir: str | Path | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)
        self._api_key = api_key
        self._data_dir = Path(data_dir) if data_dir else _DATA_DIR

    @property
    def source_name(self) -> str:
        return "esvd"

    @property
    def source_url(self) -> str:
        return "https://esvd.info/"

    @property
    def update_frequency(self) -> str:
        return "yearly"

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    # ------------------------------------------------------------------
    # Local CSV loading
    # ------------------------------------------------------------------

    def _find_csv(self) -> Path | None:
        """Locate an ESVD CSV file in the data directory."""
        if not self._data_dir.is_dir():
            return None
        # Prefer files with 'esvd' in the name, then any .csv
        candidates = sorted(self._data_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        esvd_named = [p for p in candidates if "esvd" in p.name.lower()]
        return esvd_named[0] if esvd_named else (candidates[0] if candidates else None)

    def _load_csv(
        self,
        csv_path: Path,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        biome_filter: str | None,
        service_filter: str | None,
        country_filter: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Parse a local ESVD CSV export into observation dicts."""
        w, s, e, n = bbox

        # Use utf-8-sig to strip BOM (ESVD exports include \ufeff)
        text = csv_path.read_text(encoding="utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            logger.warning("ESVD CSV %s has no header row", csv_path)
            return []

        col = _resolve_columns(list(reader.fieldnames))
        logger.debug("ESVD CSV columns resolved: %s", col)

        # At minimum we need a value column or an original-value column
        if col["value"] is None and col.get("value_original") is None:
            logger.error(
                "ESVD CSV %s: cannot find a value column among headers %s",
                csv_path, reader.fieldnames,
            )
            return []

        observations: list[dict[str, Any]] = []

        for row in reader:
            if len(observations) >= limit:
                break

            # --- value (prefer Int$/ha/yr, fall back to Original Value) ---
            raw_val = row.get(col["value"], "") if col["value"] else ""
            used_original = False
            if not raw_val or raw_val.strip() == "":
                raw_val = row.get(col.get("value_original") or "", "") if col.get("value_original") else ""
                used_original = True
            if not raw_val or raw_val.strip() == "":
                continue
            try:
                val = float(raw_val.replace(",", ""))
            except (ValueError, TypeError):
                continue

            # --- year ---
            yr_str = (
                row.get(col["study_year"], "") if col["study_year"]
                else (row.get(col["pub_year"], "") if col["pub_year"] else "")
            )
            try:
                yr = int(str(yr_str).strip()[:4]) if yr_str else time_end.year
            except (ValueError, TypeError):
                yr = time_end.year

            if yr < time_start.year or yr > time_end.year:
                continue

            ts = datetime(yr, 1, 1)

            # --- coordinates ---
            try:
                lat = float(row.get(col["latitude"], "0") or "0") if col["latitude"] else 0.0
                lon = float(row.get(col["longitude"], "0") or "0") if col["longitude"] else 0.0
            except (ValueError, TypeError):
                lat, lon = 0.0, 0.0

            # Spatial filter (skip if coordinates available and outside bbox)
            if lat != 0 and lon != 0:
                if not (w <= lon <= e and s <= lat <= n):
                    continue

            # --- biome filter ---
            biome_raw = (row.get(col["biome"], "") if col["biome"] else "").strip()
            if biome_filter and biome_filter.lower() not in biome_raw.lower():
                continue

            # Only include marine/coastal biomes (ESVD uses semicolon-separated compound biomes)
            biome_lower = biome_raw.lower()
            is_marine = any(
                kw in biome_lower
                for kw in (
                    "coral", "mangrove", "seagrass", "algae", "estuar",
                    "coastal", "salt marsh", "ocean", "continental shelf",
                    "deep sea", "marine", "reef", "kelp", "tidal",
                    "shoreline",
                )
            )
            if not is_marine and biome_raw:
                continue

            # --- service filter ---
            svc_cat = (row.get(col["service_category"], "") if col["service_category"] else "").strip()
            if service_filter and service_filter.lower() not in svc_cat.lower():
                continue

            # --- country filter ---
            country_raw = (row.get(col["country"], "") if col["country"] else "").strip()
            if country_filter and country_filter.lower() not in country_raw.lower():
                continue

            # --- build observation ---
            vid = (row.get(col["value_id"], "") if col["value_id"] else str(len(observations)))
            biome_detail = (row.get(col["biome_detail"], "") if col["biome_detail"] else "")
            eco_text = (row.get(col.get("ecosystem_text") or "", "") if col.get("ecosystem_text") else "")
            svc_name = (row.get(col["service"], "") if col["service"] else "")
            method = (row.get(col["method"], "") if col["method"] else "")
            currency = (row.get(col["currency"], "") if col["currency"] else "USD")
            reference = (row.get(col["reference"], "") if col["reference"] else "")

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],
                },
                "source_id": f"esvd-{vid}",
                "source_name": "ESVD",
                "quality_score": 0.85,
                "payload": {
                    "biome": biome_raw,
                    "biome_name": MARINE_BIOMES.get(biome_lower, biome_raw),
                    "biome_detail": biome_detail,
                    "ecosystem_text": eco_text,
                    "service_type": svc_cat,
                    "service_name": svc_name,
                    "value_per_ha_year": val,
                    "value_is_original": used_original,
                    "currency": currency,
                    "valuation_method": method,
                    "country": country_raw,
                    "continent": (row.get(col["continent"], "") if col["continent"] else ""),
                    "study_year": yr,
                    "reference": reference,
                    "scale": (row.get(col["scale"], "") if col["scale"] else ""),
                    "area_ha": (row.get(col["area_ha"], "") if col["area_ha"] else ""),
                    "protected_area": (row.get(col["protected"], "") if col["protected"] else ""),
                },
            })

        logger.info(
            "ESVD local CSV (%s) returned %d ecosystem valuations",
            csv_path.name, len(observations),
        )
        return observations

    # ------------------------------------------------------------------
    # Main fetch
    # ------------------------------------------------------------------

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch ESVD ecosystem valuation data.

        Tries local CSV first, falls back to the REST API.

        Extra params:
            biome: ecosystem type filter (default: all marine)
            service_type: 'provisioning', 'regulating', 'habitat', 'cultural'
            country: country name
            limit: max records (default: 500)
        """
        biome = params.get("biome")
        service_type = params.get("service_type")
        country = params.get("country")
        limit = params.get("limit", 500)

        # --- Try local CSV first ---
        csv_path = self._find_csv()
        if csv_path is not None:
            logger.info("ESVD: loading from local CSV %s", csv_path)
            return self._load_csv(
                csv_path, bbox, time_start, time_end,
                biome_filter=biome,
                service_filter=service_type,
                country_filter=country,
                limit=limit,
            )

        # --- Fallback: REST API (requires registration) ---
        logger.info("ESVD: no local CSV found in %s, trying REST API", self._data_dir)

        url = f"{BASE_URL}/values"
        query: dict[str, Any] = {
            "biome_type": "marine",
            "limit": limit,
            "format": "json",
        }
        if biome:
            query["biome"] = biome
        if service_type:
            query["service_type"] = service_type
        if country:
            query["country"] = country

        try:
            resp = await self._request(
                "GET", url, params=query, headers=self._headers(),
            )
            data = resp.json()
        except Exception as exc:
            logger.error("ESVD fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("data", data.get("values", []))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            study_year = rec.get("year") or rec.get("studyYear") or rec.get("valuation_year")
            value = rec.get("value") or rec.get("unitValue") or rec.get("value_per_ha")

            if value is None:
                continue

            try:
                yr = int(study_year) if study_year else time_end.year
                ts = datetime(yr, 1, 1)
                val = float(value)
            except (ValueError, TypeError):
                continue

            lat = rec.get("latitude") or rec.get("lat") or 0
            lon = rec.get("longitude") or rec.get("lon") or 0

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lon), float(lat)],
                },
                "source_id": f"esvd-{rec.get('id', len(observations))}",
                "source_name": "ESVD",
                "quality_score": 0.85,
                "payload": {
                    "biome": rec.get("biome") or rec.get("ecosystem_type", ""),
                    "biome_name": MARINE_BIOMES.get(
                        rec.get("biome", ""), rec.get("biome_name", ""),
                    ),
                    "service_type": rec.get("serviceType") or rec.get("service_category", ""),
                    "service_name": rec.get("serviceName") or rec.get("service", ""),
                    "value_per_ha_year": val,
                    "currency": rec.get("currency", "USD"),
                    "valuation_method": rec.get("method") or rec.get("valuation_method", ""),
                    "country": rec.get("country") or rec.get("Country", ""),
                    "study_year": yr,
                    "reference": rec.get("reference") or rec.get("citation", ""),
                    "confidence": rec.get("confidence") or rec.get("reliability", ""),
                },
            })

        logger.info("ESVD returned %d ecosystem valuations", len(observations))
        return observations
