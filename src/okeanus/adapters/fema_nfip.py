"""FEMA NFIP (National Flood Insurance Program) claims adapter.

2M+ flood insurance claims since 1978 with flood zone, property
type, claim amounts, and geocoded locations.

API: REST at api.openfema.gov.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fema.gov/api/open/v2"
CLAIMS_URL = f"{BASE_URL}/FimaNfipClaims"
POLICIES_URL = f"{BASE_URL}/FimaNfipPolicies"


class FemaNfipAdapter(BaseAdapter):
    """Connector for FEMA OpenFEMA — NFIP flood claims (no auth required).

    Returns flood insurance claims with amounts, flood zones, property
    types, and geographic location data.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=3.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "fema_nfip"

    @property
    def source_url(self) -> str:
        return "https://www.fema.gov/openfema"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch FEMA NFIP flood insurance claims.

        Extra params:
            state: US state FIPS code or abbreviation
            county: county name
            flood_zone: FEMA flood zone (e.g. 'A', 'V', 'AE')
            endpoint: 'claims' (default) or 'policies'
            limit: max records (default: 500)
        """
        state = params.get("state")
        county = params.get("county")
        flood_zone = params.get("flood_zone")
        endpoint = params.get("endpoint", "claims")
        limit = params.get("limit", 500)

        url = POLICIES_URL if endpoint == "policies" else CLAIMS_URL

        # Build OData filter
        filters = []
        start_str = time_start.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = time_end.strftime("%Y-%m-%dT23:59:59.999Z")

        date_field = "dateOfLoss" if endpoint == "claims" else "policyEffectiveDate"
        filters.append(f"{date_field} ge '{start_str}'")
        filters.append(f"{date_field} le '{end_str}'")

        if state:
            filters.append(f"state eq '{state}'")
        if county:
            filters.append(f"countyCode eq '{county}'")
        if flood_zone:
            filters.append(f"floodZone eq '{flood_zone}'")

        query: dict[str, Any] = {
            "$filter": " and ".join(filters),
            "$top": limit,
            "$orderby": f"{date_field} desc",
            "$format": "json",
        }

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("FEMA NFIP fetch failed: %s", exc)
            return []

        records = data.get("FimaNfipClaims", data.get("FimaNfipPolicies", []))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            date_val = rec.get(date_field, "")
            try:
                ts = datetime.fromisoformat(date_val.replace("Z", "+00:00")) if date_val else datetime.now()
            except (ValueError, TypeError):
                ts = datetime.now()

            lat = rec.get("latitude", 0)
            lon = rec.get("longitude", 0)

            if endpoint == "claims":
                payload = {
                    "type": "flood_claim",
                    "amount_paid_building": rec.get("amountPaidOnBuildingClaim"),
                    "amount_paid_contents": rec.get("amountPaidOnContentsClaim"),
                    "amount_paid_icc": rec.get("amountPaidOnIncreasedCostOfComplianceClaim"),
                    "total_paid": rec.get("totalBuildingInsuranceCoverage"),
                    "flood_zone": rec.get("floodZone", ""),
                    "state": rec.get("state", ""),
                    "county": rec.get("countyCode", ""),
                    "occupancy_type": rec.get("occupancyType", ""),
                    "date_of_loss": date_val,
                    "cause_of_damage": rec.get("causeOfDamage", ""),
                    "community_rating": rec.get("communityRatingSystemDiscount"),
                }
            else:
                payload = {
                    "type": "flood_policy",
                    "total_coverage": rec.get("totalInsurancePremiumOfThePolicy"),
                    "deductible": rec.get("deductibleAmountInBuildingCoverage"),
                    "flood_zone": rec.get("floodZone", ""),
                    "state": rec.get("state", ""),
                    "county": rec.get("countyCode", ""),
                    "policy_effective": date_val,
                }

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lon) if lon else 0, float(lat) if lat else 0],
                },
                "source_id": f"fema-{endpoint}-{rec.get('id', len(observations))}",
                "source_name": "FEMA NFIP",
                "quality_score": 0.95,
                "payload": payload,
            })

        logger.info("FEMA NFIP returned %d %s records", len(observations), endpoint)
        return observations
