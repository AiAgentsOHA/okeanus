"""Cross-domain temporal/spatial/semantic correlation engine with real statistics.

Uses scipy for significance testing, lag sweeps, cross-correlation,
and Granger causality.  DuckDB fetches raw data; scipy does the math.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from scipy import signal, stats
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Lags to test (in days)
DEFAULT_LAGS = [0, 7, 14, 30, 60, 90]
SIGNIFICANCE_THRESHOLD = 0.05
MIN_OVERLAP = 20  # minimum shared data points for a valid test


class CorrelationEngine:
    """Discover correlations across domains with real statistical methods."""

    # ------------------------------------------------------------------
    # 1a. Temporal correlation with lag sweep + significance
    # ------------------------------------------------------------------

    async def temporal_correlation(
        self,
        session: AsyncSession,
        code_a: str,
        code_b: str,
        lags: list[int] | None = None,
        min_correlation: float = 0.3,
        min_overlap: int = MIN_OVERLAP,
    ) -> list[dict[str, Any]]:
        """Test correlation between two time series at multiple lags.

        For each lag, computes Pearson and Spearman correlations with p-values.
        Returns only statistically significant results (p < 0.05).
        """
        lags = lags or DEFAULT_LAGS
        ts_a = await self._fetch_daily_series(session, code_a)
        ts_b = await self._fetch_daily_series(session, code_b)

        if len(ts_a) < min_overlap or len(ts_b) < min_overlap:
            return []

        results: list[dict[str, Any]] = []
        for lag in lags:
            aligned_a, aligned_b = self._align_series(ts_a, ts_b, lag_days=lag)
            if len(aligned_a) < min_overlap:
                continue

            arr_a = np.array(aligned_a, dtype=np.float64)
            arr_b = np.array(aligned_b, dtype=np.float64)

            # Skip constant series (zero variance)
            if np.std(arr_a) == 0 or np.std(arr_b) == 0:
                continue

            pearson_r, pearson_p = stats.pearsonr(arr_a, arr_b)
            spearman_r, spearman_p = stats.spearmanr(arr_a, arr_b)

            # Pick the stronger significant result
            for method, r_val, p_val in [
                ("pearson", float(pearson_r), float(pearson_p)),
                ("spearman", float(spearman_r), float(spearman_p)),
            ]:
                if p_val < SIGNIFICANCE_THRESHOLD and abs(r_val) >= min_correlation:
                    results.append({
                        "code_a": code_a,
                        "code_b": code_b,
                        "lag_days": lag,
                        "method": method,
                        "correlation": round(r_val, 4),
                        "p_value": round(p_val, 6),
                        "n_points": len(aligned_a),
                        "significant": True,
                    })

        # Sort by |correlation| descending
        results.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        return results

    # ------------------------------------------------------------------
    # 1b. Cross-correlation function (full lag sweep)
    # ------------------------------------------------------------------

    async def cross_correlation_function(
        self,
        session: AsyncSession,
        code_a: str,
        code_b: str,
        max_lag_days: int = 90,
    ) -> dict[str, Any]:
        """Compute normalized cross-correlation and find the peak lag.

        Returns the full CCF and the lag at which correlation is strongest.
        Useful for discovering 'A leads B by N days' patterns.
        """
        ts_a = await self._fetch_daily_series(session, code_a)
        ts_b = await self._fetch_daily_series(session, code_b)

        aligned_a, aligned_b = self._align_series(ts_a, ts_b, lag_days=0)
        if len(aligned_a) < MIN_OVERLAP:
            return {"error": f"Insufficient overlap ({len(aligned_a)} points)"}

        arr_a = np.array(aligned_a, dtype=np.float64)
        arr_b = np.array(aligned_b, dtype=np.float64)

        # Normalize to zero mean, unit variance
        arr_a = (arr_a - arr_a.mean()) / (arr_a.std() or 1.0)
        arr_b = (arr_b - arr_b.mean()) / (arr_b.std() or 1.0)

        # Full cross-correlation
        ccf = signal.correlate(arr_a, arr_b, mode="full") / len(arr_a)
        lags = signal.correlation_lags(len(arr_a), len(arr_b), mode="full")

        # Restrict to max_lag_days
        mask = np.abs(lags) <= max_lag_days
        ccf_trimmed = ccf[mask]
        lags_trimmed = lags[mask]

        # Find peak
        peak_idx = int(np.argmax(np.abs(ccf_trimmed)))
        peak_lag = int(lags_trimmed[peak_idx])
        peak_value = float(ccf_trimmed[peak_idx])

        return {
            "code_a": code_a,
            "code_b": code_b,
            "peak_lag_days": peak_lag,
            "peak_correlation": round(peak_value, 4),
            "interpretation": (
                f"{code_a} leads {code_b} by {abs(peak_lag)} days"
                if peak_lag > 0
                else f"{code_b} leads {code_a} by {abs(peak_lag)} days"
                if peak_lag < 0
                else "Synchronous correlation"
            ),
            "n_points": len(aligned_a),
            "ccf_sample": [
                {"lag": int(l), "correlation": round(float(c), 4)}
                for l, c in zip(lags_trimmed[::max(1, len(lags_trimmed) // 50)],
                                ccf_trimmed[::max(1, len(ccf_trimmed) // 50)])
            ],
        }

    # ------------------------------------------------------------------
    # 1c. Granger causality (OLS + F-test, no statsmodels needed)
    # ------------------------------------------------------------------

    async def granger_causality(
        self,
        session: AsyncSession,
        code_a: str,
        code_b: str,
        max_lag: int = 14,
        test_lags: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Test Granger causality: does past of A improve prediction of B?

        Implements the standard F-test:
        - Restricted model: B_t = sum(beta_i * B_{t-i}) + error
        - Unrestricted model: B_t = sum(beta_i * B_{t-i}) + sum(gamma_i * A_{t-i}) + error
        - F = ((RSS_r - RSS_u) / p) / (RSS_u / (n - 2p - 1))
        """
        test_lags = test_lags or [1, 3, 7, 14]
        test_lags = [l for l in test_lags if l <= max_lag]

        ts_a = await self._fetch_daily_series(session, code_a)
        ts_b = await self._fetch_daily_series(session, code_b)

        aligned_a, aligned_b = self._align_series(ts_a, ts_b, lag_days=0)
        if len(aligned_a) < max_lag + MIN_OVERLAP:
            return []

        arr_a = np.array(aligned_a, dtype=np.float64)
        arr_b = np.array(aligned_b, dtype=np.float64)

        results: list[dict[str, Any]] = []
        for lag_order in test_lags:
            # Test A -> B
            result_ab = self._granger_f_test(arr_a, arr_b, lag_order)
            if result_ab:
                result_ab.update({"cause": code_a, "effect": code_b})
                results.append(result_ab)

            # Test B -> A
            result_ba = self._granger_f_test(arr_b, arr_a, lag_order)
            if result_ba:
                result_ba.update({"cause": code_b, "effect": code_a})
                results.append(result_ba)

        # Sort by significance
        results.sort(key=lambda x: x["p_value"])
        return results

    @staticmethod
    def _granger_f_test(
        x: np.ndarray, y: np.ndarray, lag_order: int
    ) -> dict[str, Any] | None:
        """Run Granger F-test: does x Granger-cause y at given lag order?"""
        n = len(y)
        if n <= 2 * lag_order + 1:
            return None

        # Build lagged matrices
        y_target = y[lag_order:]
        n_obs = len(y_target)

        # Restricted model: only y lags
        X_restricted = np.column_stack(
            [y[lag_order - i - 1 : n - i - 1] for i in range(lag_order)]
        )
        X_restricted = np.column_stack([np.ones(n_obs), X_restricted])

        # Unrestricted model: y lags + x lags
        X_unrestricted = np.column_stack([
            X_restricted,
            *[x[lag_order - i - 1 : n - i - 1] for i in range(lag_order)],
        ])

        try:
            # OLS via least squares
            beta_r, rss_r, _, _ = np.linalg.lstsq(X_restricted, y_target, rcond=None)
            beta_u, rss_u, _, _ = np.linalg.lstsq(X_unrestricted, y_target, rcond=None)

            # Compute RSS manually if not returned (happens when rank-deficient)
            if len(rss_r) == 0:
                resid_r = y_target - X_restricted @ beta_r
                rss_r = np.array([float(resid_r @ resid_r)])
            if len(rss_u) == 0:
                resid_u = y_target - X_unrestricted @ beta_u
                rss_u = np.array([float(resid_u @ resid_u)])

            rss_r_val = float(rss_r[0])
            rss_u_val = float(rss_u[0])
            p = lag_order  # number of additional parameters
            df_resid = n_obs - 2 * lag_order - 1

            if df_resid <= 0 or rss_u_val <= 0:
                return None

            f_stat = ((rss_r_val - rss_u_val) / p) / (rss_u_val / df_resid)
            p_value = float(1 - stats.f.cdf(f_stat, p, df_resid))

            return {
                "lag_order": lag_order,
                "f_statistic": round(f_stat, 4),
                "p_value": round(p_value, 6),
                "significant": p_value < SIGNIFICANCE_THRESHOLD,
                "n_observations": n_obs,
            }
        except (np.linalg.LinAlgError, ValueError) as exc:
            logger.debug("Granger F-test failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # 1d. Auto-discover time series pairs to test
    # ------------------------------------------------------------------

    async def auto_discover_pairs(
        self,
        session: AsyncSession,
        min_points: int = 30,
        max_pairs: int = 200,
    ) -> list[dict[str, Any]]:
        """Find cross-domain time series pairs worth testing.

        Groups series by source_name, then generates all cross-source pairs
        ranked by temporal overlap quality.
        """
        from okeanus.db.duckdb import get_connection, _rows_to_dicts

        conn = get_connection()
        # Get series with enough data
        sql = """
            SELECT
                code,
                source_name,
                commodity,
                country,
                count(*) AS n_points,
                min(timestamp) AS ts_start,
                max(timestamp) AS ts_end
            FROM time_series
            GROUP BY code, source_name, commodity, country
            HAVING count(*) >= ?
            ORDER BY n_points DESC
        """
        series = _rows_to_dicts(conn, sql, [min_points])
        if len(series) < 2:
            return []

        # Generate cross-source pairs ranked by overlap
        pairs: list[dict[str, Any]] = []
        for i, sa in enumerate(series):
            for sb in series[i + 1 :]:
                if sa["source_name"] == sb["source_name"]:
                    continue  # skip same-source pairs

                # Calculate temporal overlap
                overlap_start = max(sa["ts_start"], sb["ts_start"])
                overlap_end = min(sa["ts_end"], sb["ts_end"])
                if overlap_start >= overlap_end:
                    continue

                overlap_days = (overlap_end - overlap_start).days
                if overlap_days < min_points:
                    continue

                pairs.append({
                    "code_a": sa["code"],
                    "code_b": sb["code"],
                    "source_a": sa["source_name"],
                    "source_b": sb["source_name"],
                    "commodity_a": sa.get("commodity"),
                    "commodity_b": sb.get("commodity"),
                    "overlap_days": overlap_days,
                    "min_points": min(sa["n_points"], sb["n_points"]),
                })

                if len(pairs) >= max_pairs:
                    break
            if len(pairs) >= max_pairs:
                break

        # Rank by overlap quality
        pairs.sort(key=lambda x: x["overlap_days"], reverse=True)
        return pairs

    # ------------------------------------------------------------------
    # 1e. Anomaly clustering in embedding space
    # ------------------------------------------------------------------

    async def anomaly_clusters(
        self,
        session: AsyncSession,
        z_threshold: float = 3.0,
        window: int = 30,
        eps: float = 0.3,
        min_samples: int = 3,
    ) -> list[dict[str, Any]]:
        """Cluster co-occurring anomalies using DBSCAN on embeddings.

        1. Detect anomalies across all time series via z-score
        2. Fetch embeddings for anomalous time series
        3. Run DBSCAN to find clusters of semantically related anomalies
        """
        from sklearn.cluster import DBSCAN

        # Step 1: Find anomalous time series codes
        anomaly_codes = await self._detect_anomalies_bulk(session, z_threshold, window)
        if not anomaly_codes:
            return []

        # Step 2: Fetch embeddings for those series
        code_list = list(anomaly_codes.keys())[:200]  # cap to avoid huge queries
        placeholders = ", ".join(f":c{i}" for i in range(len(code_list)))
        params = {f"c{i}": code for i, code in enumerate(code_list)}

        sql = text(f"""
            SELECT source_id, text_content, embedding
            FROM embeddings
            WHERE source_type = 'timeseries'
              AND source_id::text IN ({placeholders})
            ORDER BY source_id
        """)
        rows = (await session.execute(sql, params)).fetchall()
        if len(rows) < min_samples:
            return []

        # Step 3: DBSCAN clustering
        embeddings = np.array([row.embedding for row in rows], dtype=np.float32)
        labels = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine").fit_predict(
            embeddings
        )

        # Group results by cluster
        clusters: dict[int, list[dict[str, Any]]] = {}
        for row, label in zip(rows, labels):
            if label == -1:  # noise
                continue
            if label not in clusters:
                clusters[label] = []
            code = str(row.source_id)
            clusters[label].append({
                "code": code,
                "text": row.text_content[:200] if row.text_content else "",
                "anomalies": anomaly_codes.get(code, []),
            })

        return [
            {
                "cluster_id": cid,
                "size": len(members),
                "members": members,
            }
            for cid, members in sorted(clusters.items())
        ]

    async def _detect_anomalies_bulk(
        self,
        session: AsyncSession,
        z_threshold: float,
        window: int,
    ) -> dict[str, list[dict[str, Any]]]:
        """Detect anomalies across all time series. Returns {code: [anomalies]}."""
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
                   (value - rolling_mean) / NULLIF(rolling_std, 0) AS z_score
            FROM stats
            WHERE ABS((value - rolling_mean) / NULLIF(rolling_std, 0)) >= {float(z_threshold)}
            ORDER BY code, timestamp
        """
        rows = _rows_to_dicts(conn, sql)

        result: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            code = row["code"]
            if code not in result:
                result[code] = []
            result[code].append({
                "timestamp": str(row["timestamp"]),
                "value": row["value"],
                "z_score": round(float(row["z_score"]), 3),
            })
        return result

    # ------------------------------------------------------------------
    # Spatial co-occurrence (kept from original, unchanged)
    # ------------------------------------------------------------------

    async def spatial_co_occurrence(
        self,
        session: AsyncSession,
        radius_km: float = 50.0,
        min_events: int = 3,
    ) -> list[dict[str, Any]]:
        """Find spatially co-occurring events from different sources."""
        sql = text("""
            WITH event_pairs AS (
                SELECT
                    e1.source_name AS source_a,
                    e2.source_name AS source_b,
                    e1.event_type AS type_a,
                    e2.event_type AS type_b,
                    COUNT(*) AS co_occurrences,
                    AVG(ST_Distance(e1.geometry::geography, e2.geometry::geography)) / 1000
                        AS avg_dist_km
                FROM events e1
                JOIN events e2 ON e1.id < e2.id
                    AND e1.source_name != e2.source_name
                    AND ST_DWithin(
                        e1.geometry::geography, e2.geometry::geography, :radius_m
                    )
                    AND ABS(EXTRACT(EPOCH FROM (e1.created_at - e2.created_at)))
                        < 86400 * 30
                WHERE e1.geometry IS NOT NULL AND e2.geometry IS NOT NULL
                GROUP BY e1.source_name, e2.source_name, e1.event_type, e2.event_type
                HAVING COUNT(*) >= :min_events
            )
            SELECT * FROM event_pairs
            ORDER BY co_occurrences DESC
            LIMIT 50
        """)
        rows = (await session.execute(sql, {
            "radius_m": radius_km * 1000,
            "min_events": min_events,
        })).fetchall()

        return [
            {
                "source_a": row.source_a,
                "source_b": row.source_b,
                "type_a": row.type_a,
                "type_b": row.type_b,
                "co_occurrences": row.co_occurrences,
                "avg_distance_km": round(float(row.avg_dist_km), 1)
                if row.avg_dist_km
                else None,
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Semantic similarity clusters (kept from original, unchanged)
    # ------------------------------------------------------------------

    async def semantic_similarity_clusters(
        self,
        session: AsyncSession,
        min_similarity: float = 0.7,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Find semantically similar items across different source types."""
        sql = text("""
            SELECT
                e1.source_id AS id_a, e1.source_type AS type_a,
                e1.text_content AS text_a,
                e2.source_id AS id_b, e2.source_type AS type_b,
                e2.text_content AS text_b,
                1 - (e1.embedding <=> e2.embedding) AS similarity
            FROM embeddings e1
            JOIN embeddings e2 ON e1.id < e2.id
                AND e1.source_type != e2.source_type
            WHERE 1 - (e1.embedding <=> e2.embedding) >= :min_sim
            ORDER BY e1.embedding <=> e2.embedding
            LIMIT :lim
        """)
        rows = (await session.execute(sql, {
            "min_sim": min_similarity, "lim": limit,
        })).fetchall()

        return [
            {
                "item_a": {
                    "id": str(row.id_a), "type": row.type_a,
                    "text": row.text_a[:200] if row.text_a else "",
                },
                "item_b": {
                    "id": str(row.id_b), "type": row.type_b,
                    "text": row.text_b[:200] if row.text_b else "",
                },
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # 1f. Enhanced full scan
    # ------------------------------------------------------------------

    async def full_scan(
        self,
        session: AsyncSession,
        max_temporal_pairs: int = 50,
    ) -> list[dict[str, Any]]:
        """Run all correlation methods and return combined ranked results.

        Enhanced from original: auto-discovers pairs, runs lag sweep,
        creates graph edges for significant discoveries.
        """
        results: list[dict[str, Any]] = []

        # 1. Semantic clusters (unchanged)
        clusters = await self.semantic_similarity_clusters(session)
        for cluster in clusters:
            results.append({
                "correlation_type": "semantic",
                "confidence": cluster["similarity"],
                "description": (
                    f"Semantic similarity between "
                    f"{cluster['item_a']['type']} and {cluster['item_b']['type']}"
                ),
                "evidence": cluster,
            })

        # 2. Spatial co-occurrence (unchanged)
        spatial = await self.spatial_co_occurrence(session)
        for sp in spatial:
            confidence = min(1.0, sp["co_occurrences"] / 10.0)
            results.append({
                "correlation_type": "spatial",
                "confidence": confidence,
                "description": (
                    f"Spatial co-occurrence: {sp['type_a']} ({sp['source_a']}) "
                    f"with {sp['type_b']} ({sp['source_b']})"
                ),
                "evidence": sp,
            })

        # 3. Auto-discover temporal pairs and run lag sweep
        try:
            pairs = await self.auto_discover_pairs(session, max_pairs=max_temporal_pairs)
            for pair in pairs:
                corrs = await self.temporal_correlation(
                    session, pair["code_a"], pair["code_b"],
                )
                for corr in corrs[:3]:  # top 3 per pair
                    results.append({
                        "correlation_type": "temporal",
                        "confidence": abs(corr["correlation"]),
                        "description": (
                            f"Temporal correlation: {corr['code_a']} ↔ {corr['code_b']} "
                            f"(lag={corr['lag_days']}d, r={corr['correlation']:.3f}, "
                            f"p={corr['p_value']:.4f})"
                        ),
                        "evidence": corr,
                    })
        except Exception as exc:
            logger.warning("Temporal auto-discovery failed: %s", exc)

        # 4. Anomaly clustering
        try:
            anomaly_cls = await self.anomaly_clusters(session)
            for cl in anomaly_cls:
                results.append({
                    "correlation_type": "anomaly_cluster",
                    "confidence": min(1.0, cl["size"] / 5.0),
                    "description": (
                        f"Anomaly cluster of {cl['size']} related time series"
                    ),
                    "evidence": cl,
                })
        except Exception as exc:
            logger.warning("Anomaly clustering failed: %s", exc)

        return sorted(results, key=lambda x: x["confidence"], reverse=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _fetch_daily_series(
        session: AsyncSession,
        code: str,
    ) -> list[tuple[datetime, float]]:
        """Fetch daily-aggregated time series from DuckDB."""
        from okeanus.db.duckdb import get_connection

        conn = get_connection()
        sql = """
            SELECT
                date_trunc('day', timestamp) AS day,
                avg(value) AS value
            FROM time_series
            WHERE code = ?
            GROUP BY day
            ORDER BY day
        """
        rows = conn.execute(sql, [code]).fetchall()
        return [(row[0], float(row[1])) for row in rows if row[1] is not None]

    @staticmethod
    def _align_series(
        ts_a: list[tuple[datetime, float]],
        ts_b: list[tuple[datetime, float]],
        lag_days: int = 0,
    ) -> tuple[list[float], list[float]]:
        """Align two time series by date, applying a lag to series B.

        If lag_days > 0, B is shifted back (A leads B).
        Returns aligned value lists.
        """
        lag = timedelta(days=lag_days)
        dict_b = {ts: val for ts, val in ts_b}

        aligned_a: list[float] = []
        aligned_b: list[float] = []

        for ts, val_a in ts_a:
            target_ts = ts + lag
            val_b = dict_b.get(target_ts)
            if val_b is not None:
                aligned_a.append(val_a)
                aligned_b.append(val_b)

        return aligned_a, aligned_b
