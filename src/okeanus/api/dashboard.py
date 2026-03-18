"""Dashboard overview — live intelligence briefing from all data layers."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter
from sqlalchemy import distinct, func, select, text
from sqlalchemy.sql import literal_column

from okeanus.adapters import ADAPTER_REGISTRY
from okeanus.config import settings
from okeanus.db.postgres import async_session_factory
from okeanus.schema.base import Observation
from okeanus.schema.vessel import VesselObservation

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"])

SHIP_TYPE_NAMES = {
    None: "Unknown", 0: "Not available",
    30: "Fishing", 31: "Towing", 33: "Dredging", 35: "Military",
    36: "Sailing", 37: "Pleasure", 40: "HSC", 52: "Tug",
    60: "Passenger", 70: "Cargo", 71: "Cargo", 72: "Cargo",
    80: "Tanker", 81: "Tanker", 89: "Tanker", 90: "Other",
}


@router.get("/dashboard")
async def dashboard_overview() -> dict[str, Any]:
    """Live intelligence briefing — what's happening in the oceans right now."""
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    async with async_session_factory() as session:
        # ---- Vessel intel ----
        vessel_count = (await session.execute(
            select(func.count(distinct(VesselObservation.mmsi)))
        )).scalar() or 0

        obs_count = (await session.execute(
            select(func.count()).select_from(VesselObservation)
        )).scalar() or 0

        type_rows = (await session.execute(
            select(VesselObservation.ship_type, func.count(distinct(VesselObservation.mmsi)))
            .group_by(VesselObservation.ship_type)
        )).all()
        vessel_types = {SHIP_TYPE_NAMES.get(t, f"Type {t}"): c for t, c in type_rows}

        # Latest position per vessel
        latest_vessels = (await session.execute(
            select(
                VesselObservation.mmsi, VesselObservation.vessel_name,
                VesselObservation.ship_type, VesselObservation.sog,
                VesselObservation.destination, VesselObservation.timestamp,
                func.ST_X(func.ST_Transform(VesselObservation.geometry, 4326)).label("lon"),
                func.ST_Y(func.ST_Transform(VesselObservation.geometry, 4326)).label("lat"),
            ).distinct(VesselObservation.mmsi)
            .order_by(VesselObservation.mmsi, VesselObservation.timestamp.desc())
            .limit(50)
        )).all()

        vessels_list = [{
            "mmsi": v.mmsi, "name": v.vessel_name or f"MMSI {v.mmsi}",
            "type": SHIP_TYPE_NAMES.get(v.ship_type, "Unknown"),
            "speed_kn": round(v.sog, 1) if v.sog else 0,
            "destination": v.destination,
            "last_seen": v.timestamp.isoformat() if v.timestamp else None,
            "lon": round(v.lon, 4) if v.lon else None,
            "lat": round(v.lat, 4) if v.lat else None,
        } for v in latest_vessels]

        # ---- Observation breakdown ----
        obs_type_rows = (await session.execute(
            select(Observation.obs_type, func.count()).group_by(Observation.obs_type)
        )).all()
        obs_by_type = {r[0]: r[1] for r in obs_type_rows}

        # Active data sources
        source_rows = (await session.execute(
            select(Observation.source_name, func.count()).group_by(Observation.source_name)
        )).all()
        active_sources = {r[0]: r[1] for r in source_rows if r[0]}

        # ---- Physical observations (ocean conditions) ----
        recent_physical = (await session.execute(
            select(
                Observation.source_name, Observation.payload, Observation.timestamp,
                func.ST_X(func.ST_Transform(Observation.geometry, 4326)).label("lon"),
                func.ST_Y(func.ST_Transform(Observation.geometry, 4326)).label("lat"),
            ).where(Observation.obs_type == "physical")
            .order_by(Observation.timestamp.desc())
            .limit(100)
        )).all()

        # Extract insights from physical data
        ocean_insights = []
        quake_events = []
        ocean_conditions = []
        for row in recent_physical:
            payload = row.payload or {}
            source = row.source_name or ""
            if "earthquake" in source.lower() or "usgs" in source.lower() or payload.get("parameter") == "earthquake_magnitude":
                mag = payload.get("value") or payload.get("magnitude")
                if mag and float(mag) >= 2.0:
                    quake_events.append({
                        "magnitude": float(mag),
                        "location": payload.get("place", payload.get("location", f"{row.lat:.1f}N, {row.lon:.1f}E")),
                        "depth_km": payload.get("depth_km"),
                        "time": row.timestamp.isoformat() if row.timestamp else None,
                        "lon": round(row.lon, 2) if row.lon else None,
                        "lat": round(row.lat, 2) if row.lat else None,
                    })
            elif "argo" in source.lower() or payload.get("parameter") in ("temperature", "salinity", "pressure"):
                ocean_conditions.append({
                    "parameter": payload.get("parameter", "unknown"),
                    "value": payload.get("value"),
                    "unit": payload.get("unit", ""),
                    "depth_m": payload.get("depth_m"),
                    "source": source,
                    "lon": round(row.lon, 2) if row.lon else None,
                    "lat": round(row.lat, 2) if row.lat else None,
                })

        # Summarize quake activity
        if quake_events:
            quake_events.sort(key=lambda x: x["magnitude"], reverse=True)
            max_mag = quake_events[0]["magnitude"]
            ocean_insights.append({
                "type": "seismic",
                "severity": "high" if max_mag >= 5.0 else "medium" if max_mag >= 3.0 else "low",
                "headline": f"{len(quake_events)} earthquakes detected this week (max M{max_mag:.1f})",
                "detail": f"Strongest: M{max_mag:.1f} near {quake_events[0]['location']}",
                "events": quake_events[:5],
            })

        # Summarize ocean conditions
        if ocean_conditions:
            temps = [c for c in ocean_conditions if c["parameter"] == "temperature" and c["value"]]
            if temps:
                avg_temp = sum(float(t["value"]) for t in temps) / len(temps)
                ocean_insights.append({
                    "type": "ocean_temp",
                    "severity": "info",
                    "headline": f"Ocean temperature avg {avg_temp:.1f}C across {len(temps)} Argo profiles",
                    "detail": f"Range: {min(float(t['value']) for t in temps):.1f}C - {max(float(t['value']) for t in temps):.1f}C",
                })

        # ---- Biological observations ----
        recent_bio = (await session.execute(
            select(
                Observation.source_name, Observation.payload, Observation.timestamp,
                func.ST_X(func.ST_Transform(Observation.geometry, 4326)).label("lon"),
                func.ST_Y(func.ST_Transform(Observation.geometry, 4326)).label("lat"),
            ).where(Observation.obs_type == "biological")
            .order_by(Observation.timestamp.desc())
            .limit(100)
        )).all()

        species_seen = {}
        bio_sources = set()
        for row in recent_bio:
            payload = row.payload or {}
            species = payload.get("species") or payload.get("scientificName") or payload.get("common_name")
            if species:
                species_seen[species] = species_seen.get(species, 0) + 1
            bio_sources.add(row.source_name)

        if species_seen:
            top_species = sorted(species_seen.items(), key=lambda x: x[1], reverse=True)[:10]
            ocean_insights.append({
                "type": "biodiversity",
                "severity": "info",
                "headline": f"{len(species_seen)} species observed from {len(bio_sources)} source(s)",
                "detail": f"Most observed: {', '.join(s[0] for s in top_species[:5])}",
                "top_species": [{"name": s, "count": c} for s, c in top_species],
            })

        # ---- Acoustic observations ----
        acoustic_count = obs_by_type.get("acoustic", 0)
        if acoustic_count > 0:
            ocean_insights.append({
                "type": "acoustic",
                "severity": "info",
                "headline": f"{acoustic_count} hydrophone observations recorded",
                "detail": "Monitoring underwater sound — whale calls, ship noise, seismic surveys",
            })

        # ---- Satellite observations ----
        sat_count = obs_by_type.get("satellite", 0)
        if sat_count > 0:
            ocean_insights.append({
                "type": "satellite",
                "severity": "info",
                "headline": f"{sat_count} satellite passes captured",
                "detail": "Sentinel-2/3, Landsat 9, MODIS providing optical and radar coverage",
            })

    # ---- Geofence & alerts ----
    zone_count = 0
    alert_count = 0
    alert_summary: dict[str, int] = {}
    try:
        from okeanus.geofence.models import GeofenceAlert, GeofenceZone
        async with async_session_factory() as session:
            zone_count = (await session.execute(
                select(func.count()).select_from(GeofenceZone)
            )).scalar() or 0
            alert_count = (await session.execute(
                select(func.count()).select_from(GeofenceAlert)
            )).scalar() or 0
            severity_rows = (await session.execute(
                select(GeofenceAlert.severity, func.count()).group_by(GeofenceAlert.severity)
            )).all()
            alert_summary = {r[0]: r[1] for r in severity_rows}
    except Exception as e:
        logger.warning("Geofence stats: %s", e)

    if alert_count > 0:
        crit = alert_summary.get("critical", 0)
        ocean_insights.insert(0, {
            "type": "security",
            "severity": "high" if crit > 0 else "medium",
            "headline": f"{alert_count} geofence alerts across {zone_count} zones",
            "detail": f"{crit} critical alerts requiring attention" if crit else "Zone monitoring active",
            "alerts_by_severity": alert_summary,
        })

    # ---- Risk scoring (top 10 named vessels only) ----
    risk_summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    risk_vessels = []
    try:
        from okeanus.ml.risk.scoring import RiskScorer
        scorer = RiskScorer()
        named = [v for v in vessels_list if not v["name"].startswith("MMSI")]
        for v in named[:10]:
            result = await scorer.score(v["mmsi"])
            level = result.get("risk_level", "low")
            risk_summary[level] += 1
            if level in ("critical", "high", "medium"):
                risk_vessels.append({
                    "name": v["name"], "mmsi": v["mmsi"],
                    "score": result.get("composite_score", 0),
                    "level": level,
                    "summary": result.get("summary", ""),
                })
    except Exception as e:
        logger.warning("Risk scoring: %s", e)

    if risk_vessels:
        ocean_insights.insert(0 if not alert_count else 1, {
            "type": "risk",
            "severity": "high" if risk_summary.get("critical") or risk_summary.get("high") else "medium",
            "headline": f"{len(risk_vessels)} vessels flagged for elevated risk",
            "detail": "; ".join(f"{v['name']}: {v['level']} ({v['score']:.0f})" for v in risk_vessels[:3]),
            "vessels": risk_vessels,
        })

    return {
        "timestamp": now.isoformat(),
        "insights": ocean_insights,
        "vessels": {
            "total": vessel_count, "tracked_positions": obs_count,
            "by_type": vessel_types, "list": vessels_list,
        },
        "observations": {"total": sum(obs_by_type.values()), "by_type": obs_by_type},
        "risk": risk_summary,
        "alerts": {"total_zones": zone_count, "total_alerts": alert_count, "by_severity": alert_summary},
        "data_sources": {
            "registered": len(ADAPTER_REGISTRY), "active": len(active_sources),
            "active_sources": active_sources,
        },
    }
