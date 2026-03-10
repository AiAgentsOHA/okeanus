"""Tests for source adapters -- BaseAdapter interface and mocked HTTP responses."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from okeanus.adapters.base import BaseAdapter
from okeanus.adapters.cmems import CmemsAdapter
from okeanus.adapters.marine_regions import MarineRegionsAdapter
from okeanus.adapters.worms import WormsAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BBOX = (-10.0, 30.0, 10.0, 50.0)
T_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
T_END = datetime(2024, 1, 2, tzinfo=timezone.utc)


class ConcreteAdapter(BaseAdapter):
    """Minimal concrete adapter for testing the ABC."""

    @property
    def source_name(self) -> str:
        return "test"

    @property
    def source_url(self) -> str:
        return "https://example.com"

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
        return [{"source_name": self.source_name}]


def _mock_response(json_data: Any, status_code: int = 200) -> httpx.Response:
    """Build a fake httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://example.com"),
    )


# ---------------------------------------------------------------------------
# BaseAdapter tests
# ---------------------------------------------------------------------------


class TestBaseAdapter:
    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError):
            BaseAdapter()  # type: ignore[abstract]

    def test_concrete_properties(self) -> None:
        adapter = ConcreteAdapter()
        assert adapter.source_name == "test"
        assert adapter.source_url == "https://example.com"
        assert adapter.update_frequency == "daily"

    @pytest.mark.asyncio
    async def test_fetch_returns_list(self) -> None:
        adapter = ConcreteAdapter()
        result = await adapter.fetch(BBOX, T_START, T_END)
        assert isinstance(result, list)
        assert result[0]["source_name"] == "test"

    @pytest.mark.asyncio
    async def test_request_retries_on_failure(self) -> None:
        adapter = ConcreteAdapter(max_retries=2)
        call_count = 0

        async def _mock_request(*args: Any, **kwargs: Any) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.RequestError("connection failed")
            return _mock_response({"ok": True})

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = _mock_request
        mock_client.aclose = AsyncMock()

        resp = await adapter._request("GET", "https://example.com/test", client=mock_client)
        assert resp.status_code == 200
        assert call_count == 2


# ---------------------------------------------------------------------------
# MarineRegionsAdapter tests
# ---------------------------------------------------------------------------


class TestMarineRegionsAdapter:
    def test_properties(self) -> None:
        adapter = MarineRegionsAdapter()
        assert adapter.source_name == "marine_regions"

    @pytest.mark.asyncio
    async def test_get_by_mrgid(self) -> None:
        adapter = MarineRegionsAdapter()
        mock_resp = _mock_response({"MRGID": 3293, "preferredGazetteerName": "North Sea"})

        with patch.object(adapter, "_request", return_value=mock_resp):
            result = await adapter.get_by_mrgid(3293)

        assert result is not None
        assert result["MRGID"] == 3293

    @pytest.mark.asyncio
    async def test_search_by_name(self) -> None:
        adapter = MarineRegionsAdapter()
        mock_resp = _mock_response([{"MRGID": 3293, "preferredGazetteerName": "North Sea"}])

        with patch.object(adapter, "_request", return_value=mock_resp):
            results = await adapter.search_by_name("North Sea")

        assert len(results) == 1
        assert results[0]["MRGID"] == 3293

    @pytest.mark.asyncio
    async def test_fetch_delegates_to_eez(self) -> None:
        adapter = MarineRegionsAdapter()
        mock_resp = _mock_response([{"MRGID": 100, "placeType": "EEZ"}])

        with patch.object(adapter, "_request", return_value=mock_resp):
            results = await adapter.fetch(BBOX, T_START, T_END)

        assert len(results) == 1


# ---------------------------------------------------------------------------
# WormsAdapter tests
# ---------------------------------------------------------------------------


class TestWormsAdapter:
    def test_properties(self) -> None:
        adapter = WormsAdapter()
        assert adapter.source_name == "worms"

    @pytest.mark.asyncio
    async def test_get_by_aphia_id(self) -> None:
        adapter = WormsAdapter()
        record = {"AphiaID": 105838, "scientificname": "Solea solea", "rank": "Species"}
        mock_resp = _mock_response(record)

        with patch.object(adapter, "_request", return_value=mock_resp):
            result = await adapter.get_by_aphia_id(105838)

        assert result is not None
        assert result["AphiaID"] == 105838

    @pytest.mark.asyncio
    async def test_search_by_name(self) -> None:
        adapter = WormsAdapter()
        records = [{"AphiaID": 105838, "scientificname": "Solea solea"}]
        mock_resp = _mock_response(records)

        with patch.object(adapter, "_request", return_value=mock_resp):
            results = await adapter.search_by_name("Solea solea")

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_classification(self) -> None:
        adapter = WormsAdapter()
        tree = {"AphiaID": 105838, "scientificname": "Solea solea", "child": None}
        mock_resp = _mock_response(tree)

        with patch.object(adapter, "_request", return_value=mock_resp):
            result = await adapter.get_classification(105838)

        assert result is not None
        assert result["AphiaID"] == 105838

    @pytest.mark.asyncio
    async def test_fetch_with_names(self) -> None:
        adapter = WormsAdapter()
        records = [{"AphiaID": 105838, "scientificname": "Solea solea"}]
        mock_resp = _mock_response(records)

        with patch.object(adapter, "_request", return_value=mock_resp):
            results = await adapter.fetch(BBOX, T_START, T_END, names=["Solea solea"])

        assert len(results) == 1


# ---------------------------------------------------------------------------
# CmemsAdapter tests
# ---------------------------------------------------------------------------


def _mock_xarray_dataset(
    variable: str, value: float = 15.2,
) -> Any:
    """Build a minimal xarray-like Dataset for CMEMS tests."""
    import numpy as np

    try:
        import xarray as xr
    except ImportError:
        pytest.skip("xarray not installed")

    coords = {
        "time": [np.datetime64("2024-01-01T00:00:00")],
        "depth": [0.5],
        "latitude": [40.0],
        "longitude": [5.0],
    }
    data = np.array([[[[value]]]])
    ds = xr.Dataset({variable: (["time", "depth", "latitude", "longitude"], data)}, coords=coords)
    return ds


class TestCmemsAdapter:
    def test_properties(self) -> None:
        adapter = CmemsAdapter()
        assert adapter.source_name == "cmems"
        assert adapter.update_frequency == "6-hourly"

    @pytest.mark.asyncio
    async def test_get_sst(self) -> None:
        adapter = CmemsAdapter(username="u", password="p")
        ds = _mock_xarray_dataset("thetao", 15.2)

        with patch.object(adapter, "_open_dataset_sync", return_value=ds):
            results = await adapter.get_sst(BBOX, T_START, T_END)

        assert len(results) == 1
        assert results[0]["parameter"] == "SST"
        assert results[0]["unit"] == "degC"
        assert abs(results[0]["value"] - 15.2) < 0.01
        assert results[0]["geometry"]["type"] == "Point"

    @pytest.mark.asyncio
    async def test_get_currents(self) -> None:
        adapter = CmemsAdapter(username="u", password="p")
        import numpy as np

        try:
            import xarray as xr
        except ImportError:
            pytest.skip("xarray not installed")

        coords = {
            "time": [np.datetime64("2024-01-01T00:00:00")],
            "depth": [0.5],
            "latitude": [40.0],
            "longitude": [5.0],
        }
        ds = xr.Dataset({
            "uo": (["time", "depth", "latitude", "longitude"], np.array([[[[0.3]]]])),
            "vo": (["time", "depth", "latitude", "longitude"], np.array([[[[-0.1]]]])),
        }, coords=coords)

        with patch.object(adapter, "_open_dataset_sync", return_value=ds):
            results = await adapter.get_currents(BBOX, T_START, T_END)

        assert len(results) == 2
        params = {r["parameter"] for r in results}
        assert params == {"CURRENT_U", "CURRENT_V"}

    @pytest.mark.asyncio
    async def test_fetch_default_sst(self) -> None:
        adapter = CmemsAdapter(username="u", password="p")
        ds = _mock_xarray_dataset("thetao", 15.0)

        with patch.object(adapter, "_open_dataset_sync", return_value=ds):
            results = await adapter.fetch(BBOX, T_START, T_END)

        assert len(results) == 1
        assert results[0]["parameter"] == "SST"

    @pytest.mark.asyncio
    async def test_fetch_no_credentials(self) -> None:
        adapter = CmemsAdapter()  # no username/password
        results = await adapter.fetch(BBOX, T_START, T_END)
        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_handles_error(self) -> None:
        adapter = CmemsAdapter(username="u", password="p")

        def _fail(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("connection failed")

        with patch.object(adapter, "_open_dataset_sync", side_effect=_fail):
            results = await adapter.fetch(BBOX, T_START, T_END)

        assert results == []
