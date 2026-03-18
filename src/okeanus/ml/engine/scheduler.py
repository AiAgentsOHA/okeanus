"""Periodic intelligence pipeline scheduler.

Runs two cadences:
- Every 6 hours: correlation scan + insight generation
- Weekly: full graph backfill (spatial, semantic, correlation edges)
"""

from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger(__name__)

_WEEK_SECONDS = 7 * 24 * 3600


class IntelligenceScheduler:
    """Schedule periodic correlation scans, insight generation, and graph backfill."""

    def __init__(self, interval_hours: int = 6) -> None:
        self._interval = interval_hours * 3600
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_backfill: float = 0.0

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Intelligence scheduler started (interval=%dh)", self._interval // 3600
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self._run_scan()
            except Exception as exc:
                logger.error("Scheduled scan failed: %s", exc)

            # Weekly graph backfill
            if time.monotonic() - self._last_backfill > _WEEK_SECONDS:
                try:
                    await self._run_graph_backfill()
                    self._last_backfill = time.monotonic()
                except Exception as exc:
                    logger.error("Scheduled graph backfill failed: %s", exc)

            await asyncio.sleep(self._interval)

    async def _run_scan(self) -> None:
        from okeanus.db.postgres import get_session
        from okeanus.ml.engine.orchestrator import IntelligenceOrchestrator

        orchestrator = IntelligenceOrchestrator()
        async with get_session() as session:
            results = await orchestrator.run_correlation_scan(session)
            logger.info("Correlation scan found %d results", len(results))

            # Auto-create insights from high-confidence correlations
            if results:
                from okeanus.ml.synthesis.insights import InsightManager

                mgr = InsightManager()
                created = 0
                for r in results:
                    if r.get("confidence", 0) >= 0.5:
                        await mgr.create_insight(
                            session,
                            insight_type=r.get(
                                "correlation_type", "correlation"
                            ),
                            title=r.get(
                                "description", "Auto-discovered correlation"
                            )[:500],
                            description=str(r.get("evidence", "")),
                            confidence=r["confidence"],
                            generator="scheduler",
                            status="candidate",
                        )
                        created += 1
                logger.info("Created %d candidate insights from scan", created)

    async def _run_graph_backfill(self) -> None:
        """Run the full graph backfill pipeline (weekly cadence).

        Builds spatial, semantic, and correlation edges from existing data.
        """
        from okeanus.db.postgres import get_session
        from okeanus.ml.engine.orchestrator import IntelligenceOrchestrator

        orchestrator = IntelligenceOrchestrator()
        async with get_session() as session:
            counts = await orchestrator.run_backfill(
                session, run_correlations=False
            )
            logger.info("Graph backfill complete: %s", counts)
