"""Geospatial analytics engine for ocean observation data.

Provides spatial clustering (DBSCAN), hotspot analysis (Getis-Ord Gi*),
trajectory analysis, encounter detection, spatial autocorrelation (Moran's I),
and kernel density estimation using PostGIS + sklearn + scipy.
"""

from __future__ import annotations

import logging
import math
import uuid
from collections import defaultdict
from typing import Any

import numpy as np
from scipy import stats
from sklearn.cluster import DBSCAN
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.schema.base import Observation

logger = logging.getLogger(__name__)


class GeospatialEngine:
    """Spatial analytics on ocean observations backed by PostGIS."""

    async def spatial_clusters(
        self,
        session: AsyncSession,
        eps_km: float = 50.0,
        min_samples: int = 5,
        obs_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """DBSCAN clustering on observation coordinates.

        Uses PostGIS to extract coordinates, sklearn DBSCAN for clustering.
        Returns list of clusters with centroid, size, bbox, dominant sources.
        """
        conditions = ["geometry IS NOT NULL"]
        params: dict[str, Any] = {}
        if obs_type:
            conditions.append("obs_type = :obs_type")
            params["obs_type"] = obs_type

        where = " AND ".join(conditions)
        sql = text(f"""
            SELECT id, ST_X(ST_Centroid(geometry)) AS lon, ST_Y(ST_Centroid(geometry)) AS lat,
                   source_name, obs_type
            FROM observations
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT 50000
        """)
        result = await session.execute(sql, params)
        rows = result.fetchall()

        if len(rows) < min_samples:
            return []

        ids = [str(r.id) for r in rows]
        coords = np.array([[r.lat, r.lon] for r in rows])
        sources = [r.source_name for r in rows]
        obs_types = [r.obs_type for r in rows]

        # Convert eps from km to radians for haversine
        eps_rad = eps_km / 6371.0

        clustering = DBSCAN(
            eps=eps_rad,
            min_samples=min_samples,
            metric="haversine",
            algorithm="ball_tree",
        )
        coords_rad = np.radians(coords)
        labels = clustering.fit_predict(coords_rad)

        # Build cluster summaries
        cluster_map: dict[int, list[int]] = defaultdict(list)
        for idx, label in enumerate(labels):
            if label >= 0:
                cluster_map[label].append(idx)

        clusters: list[dict[str, Any]] = []
        for label, indices in sorted(cluster_map.items()):
            pts = coords[indices]
            srcs = [sources[i] for i in indices]
            types = [obs_types[i] for i in indices]
            src_counts: dict[str, int] = defaultdict(int)
            type_counts: dict[str, int] = defaultdict(int)
            for s in srcs:
                src_counts[s] += 1
            for t in types:
                type_counts[t] += 1

            clusters.append({
                "cluster_id": label,
                "size": len(indices),
                "centroid": {
                    "lat": round(float(pts[:, 0].mean()), 5),
                    "lon": round(float(pts[:, 1].mean()), 5),
                },
                "bbox": {
                    "south": round(float(pts[:, 0].min()), 5),
                    "north": round(float(pts[:, 0].max()), 5),
                    "west": round(float(pts[:, 1].min()), 5),
                    "east": round(float(pts[:, 1].max()), 5),
                },
                "dominant_sources": sorted(
                    src_counts.items(), key=lambda x: x[1], reverse=True
                )[:5],
                "obs_types": dict(type_counts),
            })

        clusters.sort(key=lambda c: c["size"], reverse=True)
        return clusters

    async def hotspot_analysis(
        self,
        session: AsyncSession,
        resolution_deg: float = 1.0,
        obs_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Getis-Ord Gi* hotspot analysis.

        Grid-based density analysis to find statistically significant
        hot/cold spots of ocean observations.
        """
        conditions = ["geometry IS NOT NULL"]
        params: dict[str, Any] = {"res": resolution_deg}
        if obs_type:
            conditions.append("obs_type = :obs_type")
            params["obs_type"] = obs_type

        where = " AND ".join(conditions)
        sql = text(f"""
            SELECT
                floor(ST_Y(ST_Centroid(geometry)) / :res) * :res AS lat_bin,
                floor(ST_X(ST_Centroid(geometry)) / :res) * :res AS lon_bin,
                count(*) AS count
            FROM observations
            WHERE {where}
            GROUP BY lat_bin, lon_bin
        """)
        result = await session.execute(sql, params)
        rows = result.fetchall()

        if len(rows) < 3:
            return []

        grid: dict[tuple[float, float], int] = {}
        for r in rows:
            grid[(float(r.lat_bin), float(r.lon_bin))] = int(r.count)

        values = np.array(list(grid.values()), dtype=float)
        global_mean = float(values.mean())
        global_std = float(values.std())
        n = len(values)

        if global_std == 0 or n < 3:
            return []

        cells: list[dict[str, Any]] = []
        keys = list(grid.keys())

        for i, (lat, lon) in enumerate(keys):
            # Neighbors: cells within 1 step in each direction
            neighbor_vals = []
            for dlat in [-resolution_deg, 0, resolution_deg]:
                for dlon in [-resolution_deg, 0, resolution_deg]:
                    nb_key = (round(lat + dlat, 5), round(lon + dlon, 5))
                    if nb_key in grid:
                        neighbor_vals.append(grid[nb_key])

            if not neighbor_vals:
                continue

            local_sum = sum(neighbor_vals)
            w = len(neighbor_vals)

            # Gi* statistic
            numerator = local_sum - global_mean * w
            s = math.sqrt((n * sum(v**2 for v in values) / n - global_mean**2))
            if s == 0:
                continue
            denominator = s * math.sqrt((n * w - w * w) / (n - 1)) if n > 1 else 1.0
            if denominator == 0:
                continue

            z_score = numerator / denominator
            p_value = 2.0 * (1.0 - stats.norm.cdf(abs(z_score)))

            if p_value < 0.1:
                classification = "hot" if z_score > 0 else "cold"
            else:
                classification = "neutral"

            cells.append({
                "lat_bin": lat,
                "lon_bin": lon,
                "count": grid[(lat, lon)],
                "z_score": round(z_score, 4),
                "p_value": round(p_value, 6),
                "classification": classification,
                "confidence": "99%" if p_value < 0.01 else "95%" if p_value < 0.05 else "90%" if p_value < 0.1 else "ns",
            })

        cells.sort(key=lambda c: abs(c["z_score"]), reverse=True)
        return cells

    async def trajectory_analysis(
        self,
        session: AsyncSession,
        min_points: int = 10,
    ) -> list[dict[str, Any]]:
        """Analyze vessel trajectories from vessel-type observations.

        Groups by MMSI, computes speed profile, heading changes,
        segment classification, total distance, duration.
        """
        sql = text("""
            SELECT mmsi, ST_X(ST_Centroid(geometry)) AS lon, ST_Y(ST_Centroid(geometry)) AS lat,
                   timestamp, payload
            FROM observations
            WHERE obs_type = 'vessel' AND mmsi IS NOT NULL
                  AND geometry IS NOT NULL
            ORDER BY mmsi, timestamp
            LIMIT 100000
        """)
        result = await session.execute(sql)
        rows = result.fetchall()

        # Group by MMSI
        vessels: dict[int, list] = defaultdict(list)
        for r in rows:
            vessels[r.mmsi].append(r)

        trajectories: list[dict[str, Any]] = []
        for mmsi, points in vessels.items():
            if len(points) < min_points:
                continue

            lats = [p.lat for p in points]
            lons = [p.lon for p in points]
            timestamps = [p.timestamp for p in points]

            # Compute speeds between consecutive points
            speeds: list[float] = []
            headings: list[float] = []
            total_dist_nm = 0.0
            for i in range(1, len(points)):
                dist = _haversine_nm(lats[i - 1], lons[i - 1], lats[i], lons[i])
                dt_hours = (timestamps[i] - timestamps[i - 1]).total_seconds() / 3600
                total_dist_nm += dist
                if dt_hours > 0:
                    speeds.append(dist / dt_hours)
                heading = math.degrees(math.atan2(
                    lons[i] - lons[i - 1], lats[i] - lats[i - 1]
                )) % 360
                headings.append(heading)

            # Heading changes
            heading_changes: list[float] = []
            for i in range(1, len(headings)):
                diff = abs(headings[i] - headings[i - 1])
                if diff > 180:
                    diff = 360 - diff
                heading_changes.append(diff)

            duration_hours = (timestamps[-1] - timestamps[0]).total_seconds() / 3600

            # Classify segments
            avg_speed = float(np.mean(speeds)) if speeds else 0.0
            avg_heading_change = float(np.mean(heading_changes)) if heading_changes else 0.0

            if avg_speed < 0.5:
                dominant_behavior = "anchored"
            elif avg_speed < 2.0 and avg_heading_change > 30:
                dominant_behavior = "loitering"
            elif avg_speed > 8.0 and avg_heading_change < 15:
                dominant_behavior = "transit"
            elif avg_heading_change > 20:
                dominant_behavior = "drift"
            else:
                dominant_behavior = "mixed"

            trajectories.append({
                "mmsi": mmsi,
                "point_count": len(points),
                "start_time": timestamps[0].isoformat(),
                "end_time": timestamps[-1].isoformat(),
                "duration_hours": round(duration_hours, 2),
                "total_distance_nm": round(total_dist_nm, 2),
                "speed_profile": {
                    "mean_kn": round(avg_speed, 2),
                    "max_kn": round(float(max(speeds)), 2) if speeds else 0.0,
                    "min_kn": round(float(min(speeds)), 2) if speeds else 0.0,
                    "std_kn": round(float(np.std(speeds)), 2) if speeds else 0.0,
                },
                "heading_changes": {
                    "mean_deg": round(avg_heading_change, 2),
                    "max_deg": round(float(max(heading_changes)), 2) if heading_changes else 0.0,
                },
                "dominant_behavior": dominant_behavior,
                "bbox": {
                    "south": round(min(lats), 5),
                    "north": round(max(lats), 5),
                    "west": round(min(lons), 5),
                    "east": round(max(lons), 5),
                },
            })

        trajectories.sort(key=lambda t: t["point_count"], reverse=True)
        return trajectories

    async def encounter_detection(
        self,
        session: AsyncSession,
        proximity_km: float = 1.0,
        duration_hours: float = 1.0,
    ) -> list[dict[str, Any]]:
        """Detect vessel encounters using PostGIS spatial joins + temporal windows."""
        proximity_m = proximity_km * 1000
        sql = text("""
            WITH vessel_pairs AS (
                SELECT
                    a.mmsi AS mmsi_a,
                    b.mmsi AS mmsi_b,
                    a.timestamp AS ts_a,
                    b.timestamp AS ts_b,
                    ST_X(ST_Centroid(a.geometry)) AS lon_a, ST_Y(ST_Centroid(a.geometry)) AS lat_a,
                    ST_X(ST_Centroid(b.geometry)) AS lon_b, ST_Y(ST_Centroid(b.geometry)) AS lat_b,
                    ST_Distance(a.geometry::geography, b.geometry::geography) AS dist_m
                FROM observations a
                JOIN observations b
                    ON a.obs_type = 'vessel'
                   AND b.obs_type = 'vessel'
                   AND a.mmsi IS NOT NULL
                   AND b.mmsi IS NOT NULL
                   AND a.mmsi < b.mmsi
                   AND ST_DWithin(a.geometry::geography, b.geometry::geography, :proximity_m)
                   AND abs(extract(epoch FROM a.timestamp - b.timestamp)) < 300
                LIMIT 50000
            )
            SELECT mmsi_a, mmsi_b,
                   min(ts_a) AS first_seen,
                   max(ts_a) AS last_seen,
                   count(*) AS point_count,
                   min(dist_m) AS min_dist_m,
                   avg(dist_m) AS avg_dist_m,
                   avg(lat_a) AS lat, avg(lon_a) AS lon
            FROM vessel_pairs
            GROUP BY mmsi_a, mmsi_b
            HAVING count(*) >= 2
               AND extract(epoch FROM max(ts_a) - min(ts_a)) >= :min_duration_s
            ORDER BY count(*) DESC
        """)
        result = await session.execute(sql, {
            "proximity_m": proximity_m,
            "min_duration_s": duration_hours * 3600,
        })
        rows = result.fetchall()

        encounters: list[dict[str, Any]] = []
        for r in rows:
            duration_h = (r.last_seen - r.first_seen).total_seconds() / 3600
            encounters.append({
                "encounter_id": uuid.uuid4().hex[:12],
                "vessel_a_mmsi": r.mmsi_a,
                "vessel_b_mmsi": r.mmsi_b,
                "start_time": r.first_seen.isoformat(),
                "end_time": r.last_seen.isoformat(),
                "duration_hours": round(duration_h, 2),
                "point_count": r.point_count,
                "min_distance_m": round(float(r.min_dist_m), 1),
                "avg_distance_m": round(float(r.avg_dist_m), 1),
                "location": {
                    "lat": round(float(r.lat), 5),
                    "lon": round(float(r.lon), 5),
                },
            })

        return encounters

    async def spatial_autocorrelation(
        self,
        session: AsyncSession,
        value_field: str = "quality_score",
        resolution_deg: float = 2.0,
    ) -> dict[str, Any]:
        """Global Moran's I for spatial autocorrelation of a numeric field."""
        allowed_fields = {"quality_score"}
        if value_field not in allowed_fields:
            value_field = "quality_score"

        res = resolution_deg
        sql = text(f"""
            SELECT
                floor(ST_Y(ST_Centroid(geometry)) / :res) * :res AS lat_bin,
                floor(ST_X(ST_Centroid(geometry)) / :res) * :res AS lon_bin,
                avg({value_field}) AS avg_val,
                count(*) AS n
            FROM observations
            WHERE geometry IS NOT NULL AND {value_field} IS NOT NULL
            GROUP BY lat_bin, lon_bin
            HAVING count(*) >= 2
        """)
        result = await session.execute(sql, {"res": res})
        rows = result.fetchall()

        if len(rows) < 4:
            return {
                "morans_i": None,
                "expected_i": None,
                "z_score": None,
                "p_value": None,
                "interpretation": "insufficient_data",
                "n_cells": len(rows),
            }

        cells = [(float(r.lat_bin), float(r.lon_bin), float(r.avg_val)) for r in rows]
        values = np.array([c[2] for c in cells])
        n = len(values)
        mean_val = float(values.mean())
        deviations = values - mean_val

        # Build binary contiguity weights (queen: adjacent cells)
        w_sum = 0.0
        numerator = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                dlat = abs(cells[i][0] - cells[j][0])
                dlon = abs(cells[i][1] - cells[j][1])
                if dlat <= res * 1.1 and dlon <= res * 1.1:
                    w = 1.0
                    numerator += w * deviations[i] * deviations[j]
                    w_sum += w

        if w_sum == 0:
            return {
                "morans_i": None,
                "expected_i": None,
                "z_score": None,
                "p_value": None,
                "interpretation": "no_spatial_neighbors",
                "n_cells": n,
            }

        denominator = float(np.sum(deviations ** 2))
        if denominator == 0:
            return {
                "morans_i": None,
                "expected_i": None,
                "z_score": None,
                "p_value": None,
                "interpretation": "no_variance",
                "n_cells": n,
            }

        # Moran's I (symmetric weights counted twice)
        morans_i = (n / (2 * w_sum)) * (2 * numerator / denominator)
        expected_i = -1.0 / (n - 1)
        # Approximate z-score
        var_i = 1.0 / (n - 1)  # simplified variance
        z_score = (morans_i - expected_i) / math.sqrt(var_i) if var_i > 0 else 0.0
        p_value = 2.0 * (1.0 - stats.norm.cdf(abs(z_score)))

        if morans_i > 0.3:
            interpretation = "strong_positive_autocorrelation"
        elif morans_i > 0.1:
            interpretation = "moderate_positive_autocorrelation"
        elif morans_i < -0.1:
            interpretation = "negative_autocorrelation"
        else:
            interpretation = "random_spatial_pattern"

        return {
            "morans_i": round(morans_i, 4),
            "expected_i": round(expected_i, 4),
            "z_score": round(z_score, 4),
            "p_value": round(p_value, 6),
            "interpretation": interpretation,
            "n_cells": n,
        }

    async def density_surface(
        self,
        session: AsyncSession,
        resolution_deg: float = 0.5,
        obs_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Kernel density estimation for observation heatmap."""
        conditions = ["geometry IS NOT NULL"]
        params: dict[str, Any] = {"res": resolution_deg}
        if obs_type:
            conditions.append("obs_type = :obs_type")
            params["obs_type"] = obs_type

        where = " AND ".join(conditions)
        sql = text(f"""
            SELECT
                floor(ST_Y(ST_Centroid(geometry)) / :res) * :res AS lat_bin,
                floor(ST_X(ST_Centroid(geometry)) / :res) * :res AS lon_bin,
                count(*) AS count,
                avg(quality_score) AS avg_quality,
                min(timestamp) AS earliest,
                max(timestamp) AS latest,
                count(DISTINCT source_name) AS source_count
            FROM observations
            WHERE {where}
            GROUP BY lat_bin, lon_bin
            ORDER BY count DESC
        """)
        result = await session.execute(sql, params)
        rows = result.fetchall()

        if not rows:
            return []

        max_count = max(r.count for r in rows)
        cells: list[dict[str, Any]] = []
        for r in rows:
            cells.append({
                "lat_bin": float(r.lat_bin),
                "lon_bin": float(r.lon_bin),
                "count": r.count,
                "density": round(r.count / max_count, 4) if max_count > 0 else 0.0,
                "avg_quality": round(float(r.avg_quality), 3) if r.avg_quality else None,
                "earliest": r.earliest.isoformat() if r.earliest else None,
                "latest": r.latest.isoformat() if r.latest else None,
                "source_count": r.source_count,
            })

        return cells


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in nautical miles."""
    R_NM = 3440.065
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * R_NM * math.asin(math.sqrt(min(a, 1.0)))
