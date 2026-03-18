"""Periodic intelligence pipeline scheduler."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class IntelligenceScheduler:
    """Schedule periodic correlation scans and insight generation."""

    def __init__(self, interval_hours: int = 6) -> None:
        self._interval = interval_hours * 3600
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Intelligence scheduler started (interval=%dh)", self._interval // 3600)

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
                            insight_type=r.get("correlation_type", "correlation"),
                            title=r.get("description", "Auto-discovered correlation")[:500],
                            description=str(r.get("evidence", "")),
                            confidence=r["confidence"],
                            generator="scheduler",
                            status="candidate",
                        )
                        created += 1
                logger.info("Created %d candidate insights from scan", created)
