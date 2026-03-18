"""UN Comtrade adapter — global bilateral trade data for seafood commodities.

Provides import/export volumes and values for fish, shrimp, seaweed, fishmeal
and other marine commodities between all countries. No auth required for
basic queries.

API docs: https://comtradeapi.un.org/
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

# HS codes for marine/seafood commodities (Chapter 03 + selected)
SEAFOOD_HS_CODES = [
    "03",       # Fish, crustaceans, molluscs (chapter)
    "0301",     # Live fish
    "0302",     # Fresh/chilled fish
    "0303",     # Frozen fish
    "0304",     # Fish fillets
    "0305",     # Dried/salted/smoked fish
    "0306",     # Crustaceans
    "0307",     # Molluscs
    "0308",     # Aquatic invertebrates
    "121221",   # Seaweed
    "230120",   # Fishmeal
    "1504",     # Fish oil
]


class UnComtradeAdapter(BaseAdapter):
    """Connector for UN Comtrade bilateral trade data (seafood focus)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "un_comtrade"

    @property
    def source_url(self) -> str:
        return "https://comtradeapi.un.org/"

    @property
    def update_frequency(self) -> str:
        return "annual"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch seafood trade data from UN Comtrade.

        Extra params:
            reporter: Reporter country code (ISO3 numeric, e.g. '842' for USA)
            partner: Partner country code
            hs_code: Specific HS code (default: '03' for all fish)
            flow: 'M' for imports, 'X' for exports (default both)
            limit: Max records (default 100)
        """
        limit = params.get("limit", 100)
        reporter = params.get("reporter", "")
        partner = params.get("partner", "")
        hs_code = params.get("hs_code", "03")
        flow = params.get("flow", "")

        start_year = time_start.year
        end_year = time_end.year
        # Comtrade data lags ~1-2 years; widen range to avoid querying
        # only the current year which has no data yet
        if end_year - start_year < 3:
            start_year = end_year - 5
        period = str(end_year - 1)

        query_params: dict[str, Any] = {
            "cmdCode": hs_code,
            "period": period,
        }
        # Only add reporterCode when a specific reporter is requested;
        # omitting it returns data for all reporters (reporterCode=0 returns nothing)
        if reporter:
            query_params["reporterCode"] = reporter
        if partner:
            query_params["partnerCode"] = partner
        if flow:
            query_params["flowCode"] = flow

        try:
            resp = await self._request("GET", BASE_URL, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("UN Comtrade fetch failed: %s", exc)
            return []

        records = data.get("data", [])
        if not isinstance(records, list):
            return []

        observations: list[dict[str, Any]] = []
        for rec in records:
            if len(observations) >= limit:
                break

            period_val = rec.get("period", "")
            try:
                year = int(str(period_val)[:4])
            except (ValueError, TypeError):
                continue

            if year < start_year or year > end_year:
                continue

            ts = datetime(year, 7, 1, tzinfo=timezone.utc)
            reporter_desc = rec.get("reporterDesc", "")
            partner_desc = rec.get("partnerDesc", "")
            cmd_desc = rec.get("cmdDesc", "")
            flow_desc = rec.get("flowDesc", "")
            trade_value = rec.get("primaryValue", rec.get("TradeValue"))
            net_weight = rec.get("netWgt", rec.get("NetWeight"))

            observations.append({
                "obs_type": "trade",
                "timestamp": ts,
                "geometry": None,
                "source_id": f"comtrade-{period_val}-{rec.get('reporterCode','')}-{rec.get('cmdCode','')}",
                "source_name": "UN Comtrade",
                "quality_score": 0.95,
                "payload": {
                    "year": year,
                    "reporter": reporter_desc,
                    "partner": partner_desc,
                    "commodity": cmd_desc,
                    "hs_code": rec.get("cmdCode", ""),
                    "flow": flow_desc,
                    "trade_value_usd": trade_value,
                    "net_weight_kg": net_weight,
                    "quantity": rec.get("qty"),
                    "quantity_unit": rec.get("qtyUnitAbbr", ""),
                },
            })

        logger.info("UN Comtrade returned %d trade records", len(observations))
        return observations
