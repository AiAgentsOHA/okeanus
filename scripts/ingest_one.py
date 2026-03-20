"""Ingest a single source — designed to be called as a subprocess."""
import asyncio
import json
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/Users/mikaeel/okeanus/src")

import logging
logging.disable(logging.WARNING)

# Smaller bbox for heavy gridded data sources that timeout on global bbox
SMALL_BBOX = (-30, -10, 30, 10)  # central Atlantic
DEFAULT_BBOX = (-180, -90, 180, 90)

HEAVY_SOURCES = {
    "aviso_altimetry", "cmems", "copernicus_dataspace", "hycom",
    "icoads", "marine_heatwave", "ndbc", "noaa_deep_coral",
    "noaa_rtofs", "noaa_wrecks", "skytruth_cerulean", "iotc",
}

TIME_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
TIME_END = datetime(2026, 3, 19, tzinfo=timezone.utc)
LIMIT = 500


async def main(source_name: str):
    from okeanus.adapters import ADAPTER_REGISTRY
    from okeanus.api.ingest import _build_adapter, _dict_to_observation
    from okeanus.db.postgres import async_session_factory
    from okeanus.transform import transform, store_transform_result

    adapter = _build_adapter(source_name)
    if adapter is None:
        print(json.dumps({"source": source_name, "count": 0, "error": "no adapter"}))
        return

    bbox = SMALL_BBOX if source_name in HEAVY_SOURCES else DEFAULT_BBOX
    records = await adapter.fetch(bbox, TIME_START, TIME_END, limit=LIMIT)
    if not records:
        print(json.dumps({"source": source_name, "count": 0, "error": ""}))
        return

    stored = 0
    async with async_session_factory() as session:
        economic = [r for r in records if r.get("obs_type") == "economic"]
        other = [r for r in records if r.get("obs_type") != "economic"]
        if economic:
            try:
                result, unmapped = transform(economic)
                await store_transform_result(session, result)
                if unmapped:
                    session.add_all([_dict_to_observation(r.copy()) for r in unmapped])
            except Exception:
                await session.rollback()
                session.add_all([_dict_to_observation(r.copy()) for r in economic])
        if other:
            session.add_all([_dict_to_observation(r.copy()) for r in other])
            stored += len(other)
        await session.commit()

    print(json.dumps({"source": source_name, "count": len(records), "error": ""}))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
