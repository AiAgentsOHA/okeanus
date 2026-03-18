"""WTO Fisheries Subsidies adapter.

The WTO Agreement on Fisheries Subsidies (2022) creates a framework
for tracking harmful fishery subsidies. WTO publishes notification
data and trade statistics related to fisheries.

Data accessed via WTO Timeseries API v1.
Auth: requires a free API key (``Ocp-Apim-Subscription-Key`` header).
Register at https://apiportal.wto.org/ to obtain a subscription key.

Data source: https://data.wto.org/
OpenAPI spec: data/wto/timeseries_api.yaml (local copy)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# WTO time series API
API_URL = "https://api.wto.org/timeseries/v1"


class WtoFisheriesAdapter(BaseAdapter):
    """Connector for WTO fisheries trade/subsidy data.

    Requires a free API key from https://apiportal.wto.org/.
    Set via ``api_key`` parameter or ``WTO_API_KEY`` environment variable.

    The key is sent as the ``Ocp-Apim-Subscription-Key`` header per the
    WTO OpenAPI specification.

    Returns WTO fisheries trade statistics and subsidy notifications.
    """

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)
        self._api_key = api_key or os.environ.get("WTO_API_KEY", "")

    @property
    def source_name(self) -> str:
        return "wto_fisheries"

    @property
    def source_url(self) -> str:
        return "https://data.wto.org/"

    @property
    def update_frequency(self) -> str:
        return "yearly"

    def _headers(self) -> dict[str, str]:
        """Build request headers with API key authentication."""
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["Ocp-Apim-Subscription-Key"] = self._api_key
        return headers

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch WTO fisheries trade statistics.

        Extra params:
            reporter: reporting economy code (comma-separated, default 'all')
            indicator: WTO indicator code (default 'HS_M_0030' -- fish imports)
            partner: partner economy code (default 'default')
            limit: max records (default 500)
        """
        if not self._api_key:
            logger.warning(
                "WTO adapter requires an API key. Register at "
                "https://apiportal.wto.org/ and set WTO_API_KEY env var "
                "or pass api_key to the adapter."
            )
            return []

        limit = params.get("limit", 500)
        reporter = params.get("reporter")
        indicator = params.get("indicator", "ITS_MTV_AM")

        # Query WTO timeseries -- fisheries products (HS chapter 03)
        url = f"{API_URL}/data"

        # WTO annual trade data lags ~2 years. If the requested window
        # only covers recent years that have no data yet, automatically
        # widen the search window back 5 years so we still return results.
        start_year = time_start.year
        end_year = time_end.year
        year_ranges = [
            f"{start_year}-{end_year}",
        ]
        # Add a fallback range going back further if original is narrow
        fallback_start = min(start_year, end_year - 5)
        if fallback_start < start_year:
            year_ranges.append(f"{fallback_start}-{end_year}")

        import json as _json

        data: Any = []
        for ps_range in year_ranges:
            api_params: dict[str, Any] = {
                "i": indicator,
                "r": reporter or "all",
                "p": params.get("partner", "default"),
                "ps": ps_range,
                "max": limit,
                "fmt": "json",
                "mode": "full",
                "head": "M",   # machine-readable headings
                "lang": 1,
            }

            try:
                resp = await self._request(
                    "GET", url, params=api_params, headers=self._headers(),
                )
                # 204 No Content means no data for the requested period
                if resp.status_code == 204 or not resp.content:
                    logger.info(
                        "WTO returned no data for period %s, trying wider range",
                        ps_range,
                    )
                    continue
                # WTO API sometimes returns Windows-1252 encoded text despite
                # claiming JSON; decode with fallback to avoid UnicodeDecodeError
                text = resp.content.decode("utf-8", errors="replace")
                data = _json.loads(text)
                # Check if we actually got records
                dataset_check = data if isinstance(data, list) else data.get("Dataset", [])
                if dataset_check:
                    logger.info("WTO got data for period %s", ps_range)
                    break
                logger.info(
                    "WTO returned empty dataset for %s, trying wider range",
                    ps_range,
                )
            except Exception as exc:
                logger.error("WTO fisheries data fetch failed: %s", exc)
                continue

        if not data:
            return []

        # The API returns a JSON array of DataPointExtended objects
        dataset = data if isinstance(data, list) else data.get("Dataset", [])
        if not isinstance(dataset, list):
            dataset = []

        observations: list[dict[str, Any]] = []

        for rec in dataset:
            if len(observations) >= limit:
                break

            if not isinstance(rec, dict):
                continue

            # Field names: API returns PascalCase when head=M
            reporter_name = (
                rec.get("ReportingEconomy")
                or rec.get("reportingEconomy")
                or rec.get("reporter", "")
            )
            reporter_code = (
                rec.get("ReportingEconomyCode")
                or rec.get("reportingEconomyCode")
                or rec.get("reporterCode", "")
            )
            year = rec.get("Year") or rec.get("year")
            value = rec.get("Value") or rec.get("value")

            try:
                year_int = int(year) if year else 0
                val = float(value) if value is not None else None
            except (ValueError, TypeError):
                continue

            if not year_int:
                continue

            indicator_name = (
                rec.get("Indicator")
                or rec.get("indicator")
                or rec.get("IndicatorCode", "")
            )
            unit = (
                rec.get("Unit")
                or rec.get("unit")
                or rec.get("UnitCode", "")
            )
            product = (
                rec.get("ProductOrSector")
                or rec.get("productOrSector")
                or rec.get("product", "Fish")
            )

            observations.append({
                "obs_type": "economic",
                "timestamp": datetime(year_int, 1, 1),
                "geometry": {"type": "Point", "coordinates": [0.0, 30.0]},
                "source_id": f"wto-fish-{reporter_code}-{year_int}",
                "source_name": "WTO",
                "quality_score": 0.95,
                "payload": {
                    "reporter": reporter_name,
                    "reporter_code": reporter_code,
                    "indicator": indicator_name,
                    "indicator_code": (
                        rec.get("IndicatorCode")
                        or rec.get("indicatorCode", "")
                    ),
                    "year": year_int,
                    "value": val,
                    "unit": unit,
                    "product": product,
                    "product_code": (
                        rec.get("ProductOrSectorCode")
                        or rec.get("productOrSectorCode", "")
                    ),
                    "partner": (
                        rec.get("PartnerEconomy")
                        or rec.get("partnerEconomy", "")
                    ),
                    "partner_code": (
                        rec.get("PartnerEconomyCode")
                        or rec.get("partnerEconomyCode", "")
                    ),
                    "frequency": (
                        rec.get("Frequency")
                        or rec.get("frequency", "")
                    ),
                },
            })

        logger.info("WTO returned %d fisheries trade records", len(observations))
        return observations
