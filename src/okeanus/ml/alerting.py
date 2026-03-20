"""Anomaly detection and alerting engine.

Scans time series for z-score anomalies and CUSUM change-points,
detects spatial density anomalies, and persists Alert records.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.schema.economy import Alert

logger = logging.getLogger(__name__)


class AlertEngine:
    """Run anomaly detectors and persist alerts."""

    # ------------------------------------------------------------------
    # Time-series z-score anomalies (DuckDB)
    # ------------------------------------------------------------------

    async def scan_timeseries_anomalies(
        self,
        session: AsyncSession,
        z_threshold: float = 3.0,
        window: int = 30,
    ) -> list[Alert]:
        """Scan all time_series for z-score anomalies using DuckDB."""
        from okeanus.db.duckdb import get_connection, _rows_to_dicts

        conn = get_connection()
        sql = f"""
            WITH stats AS (
                SELECT
                    code,
                    timestamp,
                    value,
                    avg(value) OVER (
                        PARTITION BY code
                        ORDER BY timestamp
                        ROWS BETWEEN {int(window) - 1} PRECEDING AND CURRENT ROW
                    ) AS rolling_mean,
                    stddev_pop(value) OVER (
                        PARTITION BY code
                        ORDER BY timestamp
                        ROWS BETWEEN {int(window) - 1} PRECEDING AND CURRENT ROW
                    ) AS rolling_std
                FROM time_series
            )
            SELECT code, timestamp, value,
                   rolling_mean, rolling_std,
                   (value - rolling_mean) / NULLIF(rolling_std, 0) AS z_score
            FROM stats
            WHERE ABS((value - rolling_mean) / NULLIF(rolling_std, 0)) >= {float(z_threshold)}
            ORDER BY ABS((value - rolling_mean) / NULLIF(rolling_std, 0)) DESC
            LIMIT 200
        """
        rows = _rows_to_dicts(conn, sql)

        alerts: list[Alert] = []
        for row in rows:
            z = float(row["z_score"])
            severity = "CRITICAL" if abs(z) >= 5.0 else "HIGH" if abs(z) >= 4.0 else "MEDIUM"
            alert = Alert(
                id=uuid.uuid4(),
                alert_type="ANOMALY",
                severity=severity,
                source_type="time_series",
                title=f"Z-score anomaly in {row['code']}: z={z:.2f}",
                description=(
                    f"Value {row['value']} at {row['timestamp']} deviates "
                    f"{abs(z):.1f} std from rolling mean {row['rolling_mean']:.4f}"
                ),
                payload={
                    "code": row["code"],
                    "timestamp": str(row["timestamp"]),
                    "value": row["value"],
                    "z_score": round(z, 3),
                    "rolling_mean": round(float(row["rolling_mean"]), 4),
                    "rolling_std": round(float(row["rolling_std"]), 4),
                },
                status="NEW",
            )
            session.add(alert)
            alerts.append(alert)

        if alerts:
            await session.flush()
            logger.info("Created %d z-score anomaly alerts", len(alerts))
        return alerts

    # ------------------------------------------------------------------
    # CUSUM change-point detection
    # ------------------------------------------------------------------

    async def scan_changepoints(
        self,
        session: AsyncSession,
        sensitivity: float = 0.05,
    ) -> list[Alert]:
        """CUSUM change-point detection on time series."""
        from okeanus.db.duckdb import get_connection, _rows_to_dicts

        conn = get_connection()
        # Get distinct codes with enough data
        codes_sql = """
            SELECT code, count(*) AS n
            FROM time_series
            GROUP BY code
            HAVING count(*) >= 30
        """
        codes = _rows_to_dicts(conn, codes_sql)

        alerts: list[Alert] = []
        for code_row in codes[:100]:  # cap to avoid long scans
            code = code_row["code"]
            data_sql = """
                SELECT timestamp, value
                FROM time_series
                WHERE code = ?
                ORDER BY timestamp
            """
            rows = conn.execute(data_sql, [code]).fetchall()
            if len(rows) < 30:
                continue

            values = np.array([float(r[1]) for r in rows], dtype=np.float64)
            timestamps = [r[0] for r in rows]

            # CUSUM algorithm
            mean_val = np.mean(values)
            std_val = np.std(values)
            if std_val == 0:
                continue

            threshold = sensitivity * len(values)
            s_pos = np.zeros(len(values))
            s_neg = np.zeros(len(values))

            for i in range(1, len(values)):
                normalized = (values[i] - mean_val) / std_val
                s_pos[i] = max(0, s_pos[i - 1] + normalized - 0.5)
                s_neg[i] = max(0, s_neg[i - 1] - normalized - 0.5)

                if s_pos[i] > threshold or s_neg[i] > threshold:
                    direction = "upward" if s_pos[i] > threshold else "downward"
                    alert = Alert(
                        id=uuid.uuid4(),
                        alert_type="CHANGE_POINT",
                        severity="HIGH",
                        source_type="time_series",
                        title=f"Change point in {code}: {direction} shift at {timestamps[i]}",
                        description=(
                            f"CUSUM detected {direction} shift at index {i}/{len(values)}. "
                            f"Value={values[i]:.4f}, mean={mean_val:.4f}, std={std_val:.4f}"
                        ),
                        payload={
                            "code": code,
                            "timestamp": str(timestamps[i]),
                            "direction": direction,
                            "cusum_value": round(float(max(s_pos[i], s_neg[i])), 3),
                            "threshold": round(threshold, 3),
                            "value": round(float(values[i]), 4),
                        },
                        status="NEW",
                    )
                    session.add(alert)
                    alerts.append(alert)
                    # Reset CUSUM after detection
                    s_pos[i] = 0
                    s_neg[i] = 0

        if alerts:
            await session.flush()
            logger.info("Created %d change-point alerts", len(alerts))
        return alerts

    # ------------------------------------------------------------------
    # Spatial density anomalies
    # ------------------------------------------------------------------

    async def scan_spatial_anomalies(
        self,
        session: AsyncSession,
        radius_km: float = 100,
    ) -> list[Alert]:
        """Detect unusual observation density clusters via DuckDB."""
        from okeanus.db.duckdb import get_connection, _rows_to_dicts

        conn = get_connection()
        # Grid-based density with z-score across cells
        resolution = radius_km / 111.0  # rough degrees
        sql = f"""
            WITH grid AS (
                SELECT
                    floor(ST_Y(ST_Centroid(geometry)) / {resolution}) * {resolution} AS lat_bin,
                    floor(ST_X(ST_Centroid(geometry)) / {resolution}) * {resolution} AS lon_bin,
                    count(*) AS density
                FROM observations
                WHERE geometry IS NOT NULL
                GROUP BY lat_bin, lon_bin
            ),
            stats AS (
                SELECT
                    avg(density) AS mean_density,
                    stddev_pop(density) AS std_density
                FROM grid
            )
            SELECT g.lat_bin, g.lon_bin, g.density,
                   (g.density - s.mean_density) / NULLIF(s.std_density, 0) AS z_score
            FROM grid g, stats s
            WHERE (g.density - s.mean_density) / NULLIF(s.std_density, 0) >= 3.0
            ORDER BY z_score DESC
            LIMIT 50
        """
        try:
            rows = _rows_to_dicts(conn, sql)
        except Exception as exc:
            logger.warning("Spatial anomaly scan failed: %s", exc)
            return []

        alerts: list[Alert] = []
        for row in rows:
            z = float(row["z_score"])
            severity = "HIGH" if z >= 5.0 else "MEDIUM"
            alert = Alert(
                id=uuid.uuid4(),
                alert_type="PATTERN",
                severity=severity,
                source_type="observations",
                title=f"Spatial density anomaly at ({row['lat_bin']:.1f}, {row['lon_bin']:.1f})",
                description=(
                    f"Observation density {row['density']} is {z:.1f} std above mean "
                    f"in grid cell ({row['lat_bin']:.2f}, {row['lon_bin']:.2f})"
                ),
                payload={
                    "lat_bin": round(float(row["lat_bin"]), 2),
                    "lon_bin": round(float(row["lon_bin"]), 2),
                    "density": row["density"],
                    "z_score": round(z, 3),
                },
                status="NEW",
            )
            session.add(alert)
            alerts.append(alert)

        if alerts:
            await session.flush()
            logger.info("Created %d spatial anomaly alerts", len(alerts))
        return alerts

    # ------------------------------------------------------------------
    # Full scan
    # ------------------------------------------------------------------

    async def run_full_scan(self, session: AsyncSession) -> dict[str, int]:
        """Run all detectors, persist alerts, return counts by type."""
        counts: dict[str, int] = {}

        try:
            ts_alerts = await self.scan_timeseries_anomalies(session)
            counts["ANOMALY"] = len(ts_alerts)
        except Exception as exc:
            logger.error("Timeseries anomaly scan failed: %s", exc)
            counts["ANOMALY"] = 0

        try:
            cp_alerts = await self.scan_changepoints(session)
            counts["CHANGE_POINT"] = len(cp_alerts)
        except Exception as exc:
            logger.error("Changepoint scan failed: %s", exc)
            counts["CHANGE_POINT"] = 0

        try:
            sp_alerts = await self.scan_spatial_anomalies(session)
            counts["PATTERN"] = len(sp_alerts)
        except Exception as exc:
            logger.error("Spatial anomaly scan failed: %s", exc)
            counts["PATTERN"] = 0

        await session.commit()
        logger.info("Full scan complete: %s", counts)
        return counts

    # ------------------------------------------------------------------
    # Query / manage alerts
    # ------------------------------------------------------------------

    async def get_alerts(
        self,
        session: AsyncSession,
        status: str | None = None,
        severity: str | None = None,
        alert_type: str | None = None,
        limit: int = 50,
    ) -> list[Alert]:
        """Query alerts with optional filters."""
        stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(Alert.status == status)
        if severity:
            stmt = stmt.where(Alert.severity == severity)
        if alert_type:
            stmt = stmt.where(Alert.alert_type == alert_type)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def acknowledge_alert(
        self,
        session: AsyncSession,
        alert_id: uuid.UUID,
        resolved_by: str | None = None,
    ) -> Alert | None:
        """Mark alert as acknowledged."""
        stmt = select(Alert).where(Alert.id == alert_id)
        result = await session.execute(stmt)
        alert = result.scalar_one_or_none()
        if alert is None:
            return None
        alert.status = "ACKNOWLEDGED"
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = resolved_by
        await session.flush()
        return alert
