"""Lightweight data refresh scheduler -- asyncio-native, no APScheduler."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    """A single scheduled job."""

    name: str
    interval_seconds: float
    func: Callable[[], Awaitable[None]]
    consecutive_failures: int = 0
    last_run: datetime | None = None
    last_error: str | None = None
    _task: asyncio.Task | None = field(default=None, repr=False)


class DataRefreshScheduler:
    """Simple asyncio-based scheduler for periodic data refresh tasks."""

    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._running = False

    def register(
        self, name: str, interval_seconds: float, func: Callable[[], Awaitable[None]]
    ) -> None:
        """Register a periodic job."""
        self._jobs[name] = ScheduledJob(
            name=name, interval_seconds=interval_seconds, func=func
        )

    async def start(self) -> None:
        """Start all registered jobs."""
        self._running = True
        for job in self._jobs.values():
            job._task = asyncio.create_task(self._run_job(job))
        logger.info("Scheduler started with %d jobs", len(self._jobs))

    async def stop(self) -> None:
        """Stop all running jobs."""
        self._running = False
        for job in self._jobs.values():
            if job._task:
                job._task.cancel()
                try:
                    await job._task
                except asyncio.CancelledError:
                    pass
        logger.info("Scheduler stopped")

    def status(self) -> list[dict]:
        """Return status of all jobs."""
        return [
            {
                "name": job.name,
                "interval_seconds": job.interval_seconds,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "consecutive_failures": job.consecutive_failures,
                "last_error": job.last_error,
            }
            for job in self._jobs.values()
        ]

    async def _run_job(self, job: ScheduledJob) -> None:
        """Run a single job on its interval with backoff on failure."""
        while self._running:
            try:
                await job.func()
                job.last_run = datetime.now(timezone.utc)
                job.consecutive_failures = 0
                job.last_error = None
            except Exception as exc:
                job.consecutive_failures += 1
                job.last_error = str(exc)
                logger.error(
                    "Job '%s' failed (attempt %d): %s",
                    job.name,
                    job.consecutive_failures,
                    exc,
                )

            # Calculate sleep: normal interval or backoff after 3+ failures
            sleep_time = job.interval_seconds
            if job.consecutive_failures >= 3:
                sleep_time = min(job.interval_seconds * 5, 3600)
                logger.warning(
                    "Job '%s' backing off to %ds after %d failures",
                    job.name,
                    sleep_time,
                    job.consecutive_failures,
                )

            await asyncio.sleep(sleep_time)
