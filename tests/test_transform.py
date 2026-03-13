"""Tests for the economy transform pipeline."""
import uuid
from datetime import datetime, timezone

import pytest


class TestSanitizeGeometry:
    def test_null_island_returns_none(self):
        from okeanus.transform.pipeline import sanitize_geometry
        assert sanitize_geometry({"type": "Point", "coordinates": [0, 0]}) is None

    def test_null_island_floats_returns_none(self):
        from okeanus.transform.pipeline import sanitize_geometry
        assert sanitize_geometry({"type": "Point", "coordinates": [0.0, 0.0]}) is None

    def test_real_coords_pass_through(self):
        from okeanus.transform.pipeline import sanitize_geometry
        geom = {"type": "Point", "coordinates": [10.5, 59.9]}
        assert sanitize_geometry(geom) == geom

    def test_none_returns_none(self):
        from okeanus.transform.pipeline import sanitize_geometry
        assert sanitize_geometry(None) is None


class TestEntityUuid:
    def test_deterministic(self):
        from okeanus.transform.pipeline import entity_uuid
        a = entity_uuid("BOEM", "lease-123")
        b = entity_uuid("BOEM", "lease-123")
        assert a == b
        assert isinstance(a, uuid.UUID)

    def test_different_inputs_differ(self):
        from okeanus.transform.pipeline import entity_uuid
        a = entity_uuid("BOEM", "lease-123")
        b = entity_uuid("BOEM", "lease-456")
        assert a != b


class TestTransformDispatch:
    def test_mapped_source_dispatched(self):
        from okeanus.transform.pipeline import MAPPER_REGISTRY
        import okeanus.transform.mappers  # noqa: F401 -- ensure registration
        # FRED should be registered
        assert "FRED" in MAPPER_REGISTRY

    def test_unmapped_source_returned(self):
        from okeanus.transform.pipeline import transform
        records = [{"source_name": "unknown_source_xyz", "obs_type": "economic", "payload": {}}]
        result, unmapped = transform(records)
        assert len(unmapped) == 1
        assert unmapped[0]["source_name"] == "unknown_source_xyz"

    def test_fred_mapper_produces_timeseries(self):
        from okeanus.transform.pipeline import transform
        import okeanus.transform.mappers  # noqa: F401
        records = [{
            "obs_type": "economic",
            "timestamp": datetime(2024, 1, 15, tzinfo=timezone.utc),
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "source_id": "fred-BDI-2024-01-15",
            "source_name": "FRED",
            "quality_score": 0.98,
            "payload": {
                "series_id": "BDI",
                "series_name": "Baltic Dry Index",
                "date": "2024-01-15",
                "value": 1847.0,
                "realtime_start": "2024-01-15",
                "realtime_end": "2024-01-15",
            },
        }]
        result, unmapped = transform(records)
        assert len(unmapped) == 0
        assert len(result.time_series) == 1
        ts = result.time_series[0]
        assert ts["code"] == "BDI"
        assert ts["value"] == 1847.0


class TestMapperRegistry:
    def test_all_30_sources_registered(self):
        import okeanus.transform.mappers  # noqa: F401
        from okeanus.transform.pipeline import MAPPER_REGISTRY
        expected_sources = [
            "World Bank WDI", "FRED", "NOAA ENOW", "Eurostat",
            "UNCTAD", "UNCTAD via UNdata", "IMF PCPS", "ILO ILOSTAT", "OECD",
            "SSB Norway", "EUMOFA", "USDA GATS", "NOAA FOSS",
            "Shanghai Shipping Exchange", "Bunker Index", "OilPriceAPI", "USDA AgTransport",
            "IATI", "Green Climate Fund", "Verra VCS / CAD Trust",
            "WBA Seafood Stewardship Index",
            "FEMA NFIP", "BOEM", "Crown Estate UK", "OSPAR", "IUU Fishing Index",
            "Sea Around Us", "ICES SAG", "FAO FishStatJ", "ESVD", "ISA DeepData",
        ]
        for src in expected_sources:
            assert src in MAPPER_REGISTRY, f"Missing mapper for: {src}"
