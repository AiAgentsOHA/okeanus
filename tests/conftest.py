"""Shared test fixtures for Okeanus."""

import pytest
from fastapi.testclient import TestClient

from okeanus.main import app


@pytest.fixture
def client() -> TestClient:
    """Synchronous test client for the FastAPI app."""
    return TestClient(app)
