"""Abstract base adapter for all Okeanus data source connectors.

Every adapter inherits from BaseAdapter and implements the ``fetch`` method
to pull data from an upstream API, returning dicts that match the
corresponding schema model.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """Abstract interface for ocean data source adapters.

    Provides HTTP request helpers with retry/backoff and rate limiting so
    that concrete adapters only need to implement domain-specific logic.
    """

    def __init__(
        self,
        *,
        requests_per_second: float = 5.0,
        max_retries: int = 3,
        timeout: float = 30.0,
    ) -> None:
        self._requests_per_second = requests_per_second
        self._max_retries = max_retries
        self._timeout = timeout
        self._min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0.0
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Properties that every adapter must declare
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Short identifier for this data source (e.g. 'cmems')."""

    @property
    @abstractmethod
    def source_url(self) -> str:
        """Base URL of the upstream API."""

    @property
    @abstractmethod
    def update_frequency(self) -> str:
        """Human-readable update cadence (e.g. 'daily', '6-hourly')."""

    # ------------------------------------------------------------------
    # Core fetch method
    # ------------------------------------------------------------------

    @abstractmethod
    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch observations within a bounding box and time window.

        Parameters
        ----------
        bbox:
            (min_lon, min_lat, max_lon, max_lat) in EPSG:4326.
        time_start, time_end:
            Temporal bounds (inclusive).
        **params:
            Adapter-specific parameters.

        Returns
        -------
        list[dict]
            Each dict is compatible with the relevant ``ObservationCreate``
            Pydantic model.
        """

    # ------------------------------------------------------------------
    # HTTP helper with retries and rate limiting
    # ------------------------------------------------------------------

    async def _rate_limit(self) -> None:
        """Sleep if necessary to respect the configured rate limit."""
        if self._min_interval <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        client: httpx.AsyncClient | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Issue an HTTP request with rate limiting and exponential-backoff retries.

        Parameters
        ----------
        method:
            HTTP method (GET, POST, etc.).
        url:
            Fully-qualified URL.
        client:
            Optional pre-configured ``httpx.AsyncClient``.  A temporary one
            is created when *None*.
        params:
            Query-string parameters.
        headers:
            Additional request headers.
        json:
            JSON body for POST/PUT requests.

        Returns
        -------
        httpx.Response
            The successful response.

        Raises
        ------
        httpx.HTTPStatusError
            After all retries are exhausted.
        """
        owns_client = client is None
        if owns_client:
            client = httpx.AsyncClient(timeout=self._timeout)

        last_exc: Exception | None = None
        try:
            for attempt in range(1, self._max_retries + 1):
                await self._rate_limit()
                try:
                    response = await client.request(
                        method, url, params=params, headers=headers, json=json,
                    )
                    response.raise_for_status()
                    return response
                except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                    last_exc = exc
                    if attempt < self._max_retries:
                        wait = 2 ** (attempt - 1)
                        logger.warning(
                            "%s request %s attempt %d/%d failed: %s — retrying in %ds",
                            self.source_name, url, attempt, self._max_retries, exc, wait,
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.error(
                            "%s request %s failed after %d attempts: %s",
                            self.source_name, url, self._max_retries, exc,
                        )
            raise last_exc  # type: ignore[misc]
        finally:
            if owns_client:
                await client.aclose()
