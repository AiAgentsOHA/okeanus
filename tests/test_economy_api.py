"""Tests for economy query API endpoints."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from okeanus.main import app

client = TestClient(app)


class TestEconomyEndpoints:
    def test_timeseries_endpoint_exists(self):
        # Will get 500 without DB but proves route is registered
        response = client.get("/economy/timeseries")
        assert response.status_code in (200, 500)

    def test_entities_endpoint_exists(self):
        response = client.get("/economy/entities")
        assert response.status_code in (200, 500)

    def test_flows_endpoint_exists(self):
        response = client.get("/economy/flows")
        assert response.status_code in (200, 500)

    def test_events_endpoint_exists(self):
        response = client.get("/economy/events")
        assert response.status_code in (200, 500)

    def test_assessments_endpoint_exists(self):
        response = client.get("/economy/assessments")
        assert response.status_code in (200, 500)

    def test_entity_detail_not_found(self):
        response = client.get("/economy/entities/00000000-0000-0000-0000-000000000000")
        # Should be 404 or 500 (no DB), not 422
        assert response.status_code in (404, 500)

    def test_economy_router_registered(self):
        routes = [r.path for r in app.routes]
        assert "/economy/timeseries" in routes
        assert "/economy/entities" in routes
        assert "/economy/entities/{entity_id}" in routes
