"""Individual risk factor calculators.

Each factor examines one dimension of vessel risk and produces a score
in [0.0, 1.0] along with human-readable evidence items that explain
the score.

Factors:
  - Flag state risk (IUU index by country)
  - AIS gap risk (dark periods)
  - Behavioral risk (suspicious movement patterns)
  - Encounter risk (rendezvous / STS transfer patterns)
  - Geofence violation risk (restricted zone intrusions)
  - Identity risk (vessel identity anomalies)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskFactor:
    """Result from a single risk factor evaluation."""

    name: str
    score: float  # 0.0 - 1.0
    weight: float  # factor weight in composite
    evidence: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 4),
            "weight": self.weight,
            "weighted_score": round(self.score * self.weight, 4),
            "evidence": self.evidence,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# IUU fishing index scores by flag state (ISO 3166-1 alpha-2)
# Source: IUU Fishing Index (poseidonprinciples.org / Global Initiative)
# Higher = worse compliance.  Normalised to 0-1 from original 1-5 scale.
# ---------------------------------------------------------------------------

# Top-40 flag states by fleet size.  Missing states default to 0.5.
FLAG_STATE_IUU_SCORES: dict[str, float] = {
    # Very high risk (FOC / poor compliance)
    "CM": 0.82, "KH": 0.80, "GH": 0.78, "SL": 0.76, "ST": 0.75,
    "TZ": 0.74, "MZ": 0.73, "MG": 0.72, "GN": 0.71, "LR": 0.70,
    # High risk
    "PA": 0.68, "HN": 0.66, "BO": 0.65, "MM": 0.64, "BD": 0.63,
    "PK": 0.62, "LK": 0.61, "TH": 0.60, "VN": 0.58, "PH": 0.57,
    # Medium risk
    "CN": 0.52, "TW": 0.50, "KR": 0.48, "IN": 0.47, "ID": 0.46,
    "TR": 0.45, "RU": 0.44, "MY": 0.43, "MX": 0.42, "BR": 0.40,
    # Low-medium risk
    "JP": 0.35, "CL": 0.34, "AR": 0.33, "ZA": 0.32, "PE": 0.31,
    "EC": 0.30, "ES": 0.28, "PT": 0.27, "IT": 0.26, "GR": 0.25,
    # Low risk (strong compliance)
    "US": 0.18, "CA": 0.17, "AU": 0.16, "NZ": 0.15, "GB": 0.14,
    "NO": 0.12, "IS": 0.11, "DK": 0.10, "SE": 0.09, "FI": 0.08,
    "DE": 0.10, "FR": 0.12, "NL": 0.10, "BE": 0.11, "IE": 0.13,
}

# AIS ship type codes → human-readable + risk weighting
SHIP_TYPE_MAP: dict[int, tuple[str, float]] = {
    # Fishing vessels — highest baseline behavioral risk
    30: ("Fishing", 0.3),
    # Cargo — moderate (smuggling, sanctions evasion)
    70: ("Cargo", 0.15), 71: ("Cargo - Hazardous A", 0.20),
    72: ("Cargo - Hazardous B", 0.18), 73: ("Cargo - Hazardous C", 0.16),
    74: ("Cargo - Hazardous D", 0.15), 79: ("Cargo - No info", 0.20),
    # Tanker — high (STS transfers, sanctions)
    80: ("Tanker", 0.25), 81: ("Tanker - Hazardous A", 0.30),
    82: ("Tanker - Hazardous B", 0.28), 83: ("Tanker - Hazardous C", 0.26),
    84: ("Tanker - Hazardous D", 0.25), 89: ("Tanker - No info", 0.30),
    # Passenger — low risk
    60: ("Passenger", 0.05), 61: ("Passenger - Hazardous A", 0.10),
    69: ("Passenger - No info", 0.10),
    # Tug / pilot / SAR — very low
    31: ("Towing", 0.05), 32: ("Towing (large)", 0.05),
    50: ("Pilot vessel", 0.02), 51: ("SAR", 0.01), 52: ("Tug", 0.05),
    # Pleasure / sailing
    36: ("Sailing", 0.03), 37: ("Pleasure craft", 0.03),
}


def _mmsi_to_flag(mmsi: int) -> str | None:
    """Extract flag state ISO code from MMSI MID (Maritime ID Digit).

    The first 3 digits of a 9-digit MMSI encode the flag state per
    ITU MID table.  Returns ISO 3166-1 alpha-2 or None.
    """
    mid_map: dict[int, str] = {
        201: "AL", 202: "AD", 203: "AT", 204: "PT", 205: "BE",
        206: "BY", 207: "BG", 208: "VA", 209: "CY", 210: "CY",
        211: "DE", 212: "CY", 213: "GE", 214: "MD", 215: "MT",
        216: "AM", 218: "DE", 219: "DK", 220: "DK", 224: "ES",
        225: "ES", 226: "FR", 227: "FR", 228: "FR", 229: "MT",
        230: "FI", 231: "FO", 232: "GB", 233: "GB", 234: "GB",
        235: "GB", 236: "GI", 237: "GR", 238: "HR", 239: "GR",
        240: "GR", 241: "GR", 242: "MA", 243: "HU", 244: "NL",
        245: "NL", 246: "NL", 247: "IT", 248: "MT", 249: "MT",
        250: "IE", 251: "IS", 252: "LI", 253: "LU", 254: "MC",
        255: "PT", 256: "MT", 257: "NO", 258: "NO", 259: "NO",
        261: "PL", 263: "PT", 264: "RO", 265: "SE", 266: "SE",
        267: "SK", 268: "SM", 269: "CH", 270: "CZ", 271: "TR",
        272: "UA", 273: "RU", 274: "MK", 275: "LV", 276: "EE",
        277: "LT", 278: "SI", 279: "RS",
        301: "AI", 303: "US", 304: "AG", 305: "AG", 306: "CW",
        307: "AW", 308: "BS", 309: "BS", 310: "BM", 311: "BS",
        312: "BZ", 314: "BB", 316: "CA", 319: "KY",
        321: "CR", 323: "CU", 325: "DM", 327: "DO",
        329: "GP", 330: "GD", 331: "GL", 332: "GT",
        334: "HN", 336: "HT", 338: "US", 339: "JM",
        341: "KN", 343: "LC", 345: "MX", 347: "MQ",
        348: "MS", 350: "NI", 351: "PA", 352: "PA", 353: "PA",
        354: "PA", 355: "PA", 356: "PA", 357: "PA",
        358: "PR", 359: "SV", 361: "PM", 362: "TT",
        364: "TC", 366: "US", 367: "US", 368: "US", 369: "US",
        370: "PA", 371: "PA", 372: "PA", 373: "PA",
        375: "VC", 376: "VC", 377: "VC",
        378: "VG", 379: "VI",
        401: "AF", 403: "SA", 405: "BD", 408: "BH",
        410: "BT", 412: "CN", 413: "CN", 414: "CN",
        416: "TW", 417: "LK", 419: "IN", 422: "IR",
        423: "AZ", 425: "IQ", 428: "IL", 431: "JP",
        432: "JP", 434: "TM", 436: "KZ", 437: "UZ",
        438: "JO", 440: "KR", 441: "KR", 443: "PS",
        445: "KP", 447: "KW", 450: "LB", 451: "KG",
        453: "MO", 455: "MV", 457: "MN", 459: "NP",
        461: "OM", 463: "PK", 466: "QA", 468: "SY",
        470: "AE", 471: "AE", 472: "TJ", 473: "YE",
        475: "AF",
        501: "FR", 503: "AU", 506: "MM", 508: "BN",
        510: "FM", 511: "PW", 512: "NZ", 514: "KH",
        515: "KH", 516: "AU", 518: "CK", 520: "FJ",
        523: "CC", 525: "ID", 529: "KI", 531: "LA",
        533: "MY", 536: "MP", 538: "MH",
        540: "NC", 542: "NU", 544: "NR", 546: "FR",
        548: "PH", 553: "PG", 555: "PN",
        557: "SB", 559: "AS", 561: "WS", 563: "SG",
        564: "SG", 565: "SG", 566: "SG",
        567: "TH", 570: "TO", 572: "TV", 574: "VN",
        576: "VU", 577: "VU", 578: "WF",
        601: "ZA", 603: "AO", 605: "DZ", 607: "FR",
        608: "GB", 609: "BI", 610: "BJ", 611: "BW",
        612: "CF", 613: "CM", 615: "CG", 616: "KM",
        617: "CV", 618: "FR", 619: "CI", 620: "KM",
        621: "DJ", 622: "EG", 624: "ET", 625: "ER",
        626: "GA", 627: "GH", 629: "GM", 630: "GW",
        631: "GQ", 632: "GN", 633: "BF", 634: "KE",
        635: "FR", 636: "LR", 637: "LR", 642: "LY",
        644: "LS", 645: "MU", 647: "MG", 649: "ML",
        650: "MZ", 654: "MR", 655: "MW", 656: "NE",
        657: "NG", 659: "NA", 660: "FR", 661: "RW",
        662: "SD", 663: "SN", 664: "SC", 665: "SH",
        666: "SO", 667: "SL", 668: "ST", 669: "SZ",
        670: "TD", 671: "TG", 672: "TN", 674: "TZ",
        675: "UG", 676: "CD", 677: "TZ", 678: "ZM",
        679: "ZW",
    }
    if mmsi < 100_000_000 or mmsi > 799_999_999:
        return None
    mid = mmsi // 1_000_000
    return mid_map.get(mid)


# ---------------------------------------------------------------------------
# Factor calculators
# ---------------------------------------------------------------------------


async def calc_flag_state_risk(
    mmsi: int,
    flag_override: str | None = None,
    **_kwargs: Any,
) -> RiskFactor:
    """Score based on vessel's flag state IUU compliance index.

    Higher score = flag state with weaker fisheries enforcement.
    """
    evidence: list[str] = []

    flag = flag_override or _mmsi_to_flag(mmsi)
    if flag is None:
        return RiskFactor(
            name="flag_state",
            score=0.5,
            weight=0.15,
            evidence=["Unable to determine flag state from MMSI"],
            details={"mmsi": mmsi, "flag": None},
        )

    score = FLAG_STATE_IUU_SCORES.get(flag, 0.5)
    evidence.append(f"Flag state: {flag} (IUU index score: {score:.2f})")

    if score >= 0.65:
        evidence.append("Flag of convenience or poor compliance record")
    elif score <= 0.20:
        evidence.append("Strong fisheries enforcement regime")

    return RiskFactor(
        name="flag_state",
        score=score,
        weight=0.15,
        evidence=evidence,
        details={"mmsi": mmsi, "flag": flag, "iuu_score": score},
    )


async def calc_ais_gap_risk(
    mmsi: int,
    positions: list[dict[str, Any]] | None = None,
    time_window_hours: int = 72,
    **_kwargs: Any,
) -> RiskFactor:
    """Score based on AIS transmission gaps.

    Long AIS silences suggest intentional dark activity (transponder
    switched off to avoid detection).

    Gap thresholds:
      - > 2h: notable
      - > 6h: suspicious
      - > 24h: highly suspicious
    """
    evidence: list[str] = []
    gaps: list[dict[str, Any]] = []

    if not positions or len(positions) < 2:
        # Try to fetch from DB
        positions = await _fetch_vessel_positions(mmsi, time_window_hours)

    if not positions or len(positions) < 2:
        return RiskFactor(
            name="ais_gap",
            score=0.0,
            weight=0.20,
            evidence=["Insufficient position data to assess AIS gaps"],
            details={"mmsi": mmsi, "gap_count": 0},
        )

    # Sort by timestamp
    sorted_pos = sorted(positions, key=lambda p: p.get("timestamp", ""))
    total_gap_hours = 0.0
    max_gap_hours = 0.0

    for i in range(1, len(sorted_pos)):
        t0 = _parse_ts(sorted_pos[i - 1].get("timestamp"))
        t1 = _parse_ts(sorted_pos[i].get("timestamp"))
        if t0 is None or t1 is None:
            continue
        gap = (t1 - t0).total_seconds() / 3600.0
        if gap >= 2.0:
            gaps.append({
                "start": t0.isoformat(),
                "end": t1.isoformat(),
                "hours": round(gap, 2),
            })
            total_gap_hours += gap
            max_gap_hours = max(max_gap_hours, gap)

    # Score calculation
    if max_gap_hours >= 24:
        score = min(1.0, 0.8 + (max_gap_hours - 24) / 120)
        evidence.append(f"CRITICAL: {max_gap_hours:.1f}h AIS gap detected (>24h)")
    elif max_gap_hours >= 6:
        score = 0.5 + (max_gap_hours - 6) / 36  # 0.5 at 6h → 0.8 at 24h
        evidence.append(f"Suspicious {max_gap_hours:.1f}h AIS gap (>6h)")
    elif max_gap_hours >= 2:
        score = 0.15 + (max_gap_hours - 2) / 16  # 0.15 at 2h → 0.4 at 6h
        evidence.append(f"Notable {max_gap_hours:.1f}h AIS gap")
    else:
        score = 0.0
        evidence.append("No significant AIS gaps")

    # Multiple gaps compound the score
    if len(gaps) >= 3:
        score = min(1.0, score + 0.1)
        evidence.append(f"Multiple gaps detected: {len(gaps)} gaps in {time_window_hours}h window")

    evidence.append(f"Total dark time: {total_gap_hours:.1f}h across {len(gaps)} gaps")

    return RiskFactor(
        name="ais_gap",
        score=min(1.0, score),
        weight=0.20,
        evidence=evidence,
        details={
            "mmsi": mmsi,
            "gap_count": len(gaps),
            "max_gap_hours": round(max_gap_hours, 2),
            "total_gap_hours": round(total_gap_hours, 2),
            "gaps": gaps[:10],  # top 10 gaps
        },
    )


async def calc_behavioral_risk(
    mmsi: int,
    trajectory_segments: list[dict[str, Any]] | None = None,
    **_kwargs: Any,
) -> RiskFactor:
    """Score based on suspicious movement patterns.

    Red flags:
      - Fishing behavior in non-fishing areas
      - Excessive loitering
      - Unusual maneuvering patterns
      - Speed anomalies (too slow for claimed type, too fast for conditions)
    """
    evidence: list[str] = []
    score = 0.0

    if trajectory_segments is None:
        # Try to classify from DB
        try:
            from okeanus.ml.behavioral.trajectory import classify_vessel_track

            segments = await classify_vessel_track(mmsi=mmsi, window_minutes=60)
            trajectory_segments = [s.to_dict() for s in segments]
        except Exception:
            trajectory_segments = []

    if not trajectory_segments:
        return RiskFactor(
            name="behavioral",
            score=0.0,
            weight=0.20,
            evidence=["No trajectory data available"],
            details={"mmsi": mmsi},
        )

    # Analyze behavior distribution
    behavior_time: dict[str, float] = {}
    total_minutes = 0.0
    for seg in trajectory_segments:
        behavior = seg.get("behavior", "unknown")
        duration = seg.get("duration_minutes", 0.0)
        behavior_time[behavior] = behavior_time.get(behavior, 0.0) + duration
        total_minutes += duration

    if total_minutes == 0:
        return RiskFactor(
            name="behavioral",
            score=0.0,
            weight=0.20,
            evidence=["No significant trajectory duration"],
            details={"mmsi": mmsi},
        )

    # Fishing time ratio (suspicious if vessel isn't classified as fishing type)
    fishing_pct = behavior_time.get("fishing", 0) / total_minutes
    if fishing_pct > 0.3:
        score += 0.3
        evidence.append(f"Fishing behavior {fishing_pct:.0%} of observed time")

    # Loitering (possible surveillance, waiting for STS)
    loitering_pct = behavior_time.get("loitering", 0) / total_minutes
    if loitering_pct > 0.2:
        score += 0.2
        evidence.append(f"Loitering {loitering_pct:.0%} of observed time")

    # Excessive maneuvering (evasion patterns)
    maneuvering_pct = behavior_time.get("maneuvering", 0) / total_minutes
    if maneuvering_pct > 0.3:
        score += 0.15
        evidence.append(f"Heavy maneuvering {maneuvering_pct:.0%} — possible evasion")

    # Drifting (possible disabled vessel or AIS spoofing)
    drifting_pct = behavior_time.get("drifting", 0) / total_minutes
    if drifting_pct > 0.4:
        score += 0.1
        evidence.append(f"Drifting {drifting_pct:.0%} — possible disable/spoof")

    # Low confidence segments (erratic or hard to classify)
    low_conf = [s for s in trajectory_segments if s.get("confidence", 1.0) < 0.4]
    if len(low_conf) > len(trajectory_segments) * 0.3:
        score += 0.1
        evidence.append("Many low-confidence behavioral classifications — erratic movement")

    if not evidence:
        evidence.append("Normal vessel movement patterns")

    return RiskFactor(
        name="behavioral",
        score=min(1.0, score),
        weight=0.20,
        evidence=evidence,
        details={
            "mmsi": mmsi,
            "behavior_distribution": {
                k: {"minutes": round(v, 1), "pct": round(v / total_minutes, 3)}
                for k, v in behavior_time.items()
            },
            "total_minutes": round(total_minutes, 1),
        },
    )


async def calc_encounter_risk(
    mmsi: int,
    encounters: list[dict[str, Any]] | None = None,
    **_kwargs: Any,
) -> RiskFactor:
    """Score based on suspicious vessel-to-vessel encounters.

    Red flags:
      - Rendezvous events (possible STS / transshipment)
      - Multiple encounters in short period
      - Encounters with high-risk vessels
      - Extended close-proximity meetings
    """
    evidence: list[str] = []
    score = 0.0

    if encounters is None:
        try:
            from okeanus.ml.behavioral.encounters import detect_encounters_for_vessel

            enc_objects = await detect_encounters_for_vessel(mmsi=mmsi)
            encounters = [e.to_dict() for e in enc_objects]
        except Exception:
            encounters = []

    if not encounters:
        return RiskFactor(
            name="encounter",
            score=0.0,
            weight=0.15,
            evidence=["No encounters detected"],
            details={"mmsi": mmsi, "encounter_count": 0},
        )

    # Count by type and risk level
    by_type: dict[str, int] = {}
    by_risk: dict[str, int] = {}
    rendezvous_count = 0
    high_risk_count = 0

    for enc in encounters:
        etype = enc.get("encounter_type", "unknown")
        erisk = enc.get("risk_level", "low")
        by_type[etype] = by_type.get(etype, 0) + 1
        by_risk[erisk] = by_risk.get(erisk, 0) + 1

        if etype == "rendezvous":
            rendezvous_count += 1
        if erisk in ("high", "critical"):
            high_risk_count += 1

    # Score: rendezvous events are the primary risk signal
    if rendezvous_count >= 3:
        score += 0.5
        evidence.append(f"{rendezvous_count} rendezvous events — possible STS operations")
    elif rendezvous_count >= 1:
        score += 0.25
        evidence.append(f"{rendezvous_count} rendezvous event(s) detected")

    # High-risk encounters
    if high_risk_count >= 2:
        score += 0.3
        evidence.append(f"{high_risk_count} high/critical risk encounters")
    elif high_risk_count >= 1:
        score += 0.15
        evidence.append(f"{high_risk_count} high/critical risk encounter")

    # Volume of encounters
    if len(encounters) >= 5:
        score += 0.1
        evidence.append(f"High encounter volume: {len(encounters)} total")

    if not evidence:
        evidence.append("No suspicious encounter patterns")

    return RiskFactor(
        name="encounter",
        score=min(1.0, score),
        weight=0.15,
        evidence=evidence,
        details={
            "mmsi": mmsi,
            "encounter_count": len(encounters),
            "by_type": by_type,
            "by_risk": by_risk,
        },
    )


async def calc_geofence_risk(
    mmsi: int,
    alerts: list[dict[str, Any]] | None = None,
    **_kwargs: Any,
) -> RiskFactor:
    """Score based on geofence zone violations.

    Red flags:
      - Entry into MPAs (Marine Protected Areas)
      - Presence in restricted/sanctioned waters
      - Loitering in port exclusion zones
      - Speed violations in traffic separation schemes
    """
    evidence: list[str] = []
    score = 0.0

    if alerts is None:
        try:
            from okeanus.db.postgres import async_session_factory
            from okeanus.geofence.models import GeofenceAlert

            from sqlalchemy import select

            async with async_session_factory() as session:
                stmt = (
                    select(GeofenceAlert)
                    .where(GeofenceAlert.mmsi == mmsi)
                    .order_by(GeofenceAlert.triggered_at.desc())
                    .limit(50)
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()
                alerts = [
                    {
                        "rule_type": r.rule_type,
                        "severity": r.severity,
                        "triggered_at": r.triggered_at.isoformat(),
                        "details": r.details,
                    }
                    for r in rows
                ]
        except Exception:
            alerts = []

    if not alerts:
        return RiskFactor(
            name="geofence",
            score=0.0,
            weight=0.15,
            evidence=["No geofence violations recorded"],
            details={"mmsi": mmsi, "violation_count": 0},
        )

    # Score by severity
    severity_scores = {"info": 0.05, "warning": 0.1, "alert": 0.2, "critical": 0.4}
    by_severity: dict[str, int] = {}
    by_type: dict[str, int] = {}

    for alert in alerts:
        sev = alert.get("severity", "info")
        rtype = alert.get("rule_type", "unknown")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_type[rtype] = by_type.get(rtype, 0) + 1
        score += severity_scores.get(sev, 0.05)

    # Cap at 1.0
    score = min(1.0, score)

    if by_severity.get("critical", 0) > 0:
        evidence.append(
            f"{by_severity['critical']} critical geofence violation(s) — "
            "possible MPA or restricted zone intrusion"
        )
    if by_severity.get("alert", 0) > 0:
        evidence.append(f"{by_severity['alert']} alert-level violation(s)")

    for rtype, count in by_type.items():
        evidence.append(f"{count} {rtype} violation(s)")

    return RiskFactor(
        name="geofence",
        score=score,
        weight=0.15,
        evidence=evidence,
        details={
            "mmsi": mmsi,
            "violation_count": len(alerts),
            "by_severity": by_severity,
            "by_type": by_type,
        },
    )


async def calc_identity_risk(
    mmsi: int,
    vessel_info: dict[str, Any] | None = None,
    positions: list[dict[str, Any]] | None = None,
    **_kwargs: Any,
) -> RiskFactor:
    """Score based on vessel identity anomalies.

    Red flags:
      - MMSI doesn't match expected format
      - Ship type inconsistent with behavior
      - Missing IMO number (required for SOLAS vessels)
      - Vessel name anomalies
    """
    evidence: list[str] = []
    score = 0.0

    if vessel_info is None:
        vessel_info = await _fetch_vessel_info(mmsi)

    # MMSI format check
    mmsi_str = str(mmsi)
    if len(mmsi_str) != 9:
        score += 0.2
        evidence.append(f"Non-standard MMSI length: {len(mmsi_str)} digits")

    flag = _mmsi_to_flag(mmsi)
    if flag is None and len(mmsi_str) == 9:
        score += 0.15
        evidence.append("MMSI MID does not map to known flag state")

    # Missing IMO
    imo = vessel_info.get("imo")
    ship_type = vessel_info.get("ship_type")
    vessel_name = vessel_info.get("vessel_name")

    if ship_type and ship_type >= 60 and not imo:
        # SOLAS vessels (cargo, tanker, passenger) should have IMO
        score += 0.2
        evidence.append("Missing IMO number for SOLAS-class vessel")

    # Vessel name checks
    if vessel_name:
        name_upper = vessel_name.upper().strip()
        suspicious_names = [
            "UNKNOWN", "TEST", "N/A", "NONE", "DEFAULT",
            "123456", "VESSEL", "SHIP",
        ]
        if name_upper in suspicious_names or len(name_upper) <= 1:
            score += 0.15
            evidence.append(f"Suspicious vessel name: '{vessel_name}'")
    elif ship_type and ship_type >= 30:
        score += 0.1
        evidence.append("Missing vessel name")

    # Ship type consistency with behavior (if we have trajectory data)
    if ship_type and positions:
        type_name, _baseline = SHIP_TYPE_MAP.get(ship_type, ("Unknown", 0.1))
        avg_sog = _avg_sog(positions)
        if avg_sog is not None:
            # Fishing vessel transiting at high speed for extended period
            if ship_type == 30 and avg_sog > 12:
                score += 0.15
                evidence.append(
                    f"Fishing vessel ({type_name}) averaging {avg_sog:.1f} kn "
                    "— inconsistent with fishing activity"
                )
            # Cargo vessel very slow (possibly hiding / not in transit)
            if ship_type in (70, 71, 72, 73, 74, 79) and avg_sog < 2 and avg_sog > 0:
                score += 0.1
                evidence.append(
                    f"Cargo vessel averaging {avg_sog:.1f} kn — "
                    "unusually slow for transit"
                )

    if not evidence:
        evidence.append("No identity anomalies detected")

    return RiskFactor(
        name="identity",
        score=min(1.0, score),
        weight=0.15,
        evidence=evidence,
        details={
            "mmsi": mmsi,
            "flag": flag,
            "imo": imo,
            "ship_type": ship_type,
            "vessel_name": vessel_name,
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_ts(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        # Handle ISO strings with or without timezone
        s = str(val)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _avg_sog(positions: list[dict[str, Any]]) -> float | None:
    sogs = [p["sog"] for p in positions if p.get("sog") is not None]
    if not sogs:
        return None
    return sum(sogs) / len(sogs)


async def _fetch_vessel_positions(
    mmsi: int, hours: int = 72
) -> list[dict[str, Any]]:
    """Fetch recent vessel positions from DB."""
    try:
        from okeanus.db.postgres import async_session_factory
        from okeanus.schema.vessel import VesselObservation

        from sqlalchemy import select

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        async with async_session_factory() as session:
            stmt = (
                select(VesselObservation)
                .where(
                    VesselObservation.mmsi == mmsi,
                    VesselObservation.timestamp >= cutoff,
                )
                .order_by(VesselObservation.timestamp)
                .limit(500)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "sog": r.sog,
                    "cog": r.cog,
                    "heading": r.heading,
                }
                for r in rows
            ]
    except Exception as exc:
        logger.debug("Could not fetch positions for %s: %s", mmsi, exc)
        return []


async def _fetch_vessel_info(mmsi: int) -> dict[str, Any]:
    """Fetch vessel static data from most recent AIS position."""
    try:
        from okeanus.db.postgres import async_session_factory
        from okeanus.schema.vessel import VesselObservation

        from sqlalchemy import select

        async with async_session_factory() as session:
            stmt = (
                select(VesselObservation)
                .where(VesselObservation.mmsi == mmsi)
                .order_by(VesselObservation.timestamp.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                return {
                    "imo": row.imo,
                    "vessel_name": row.vessel_name,
                    "call_sign": row.call_sign,
                    "ship_type": row.ship_type,
                    "destination": row.destination,
                }
    except Exception as exc:
        logger.debug("Could not fetch vessel info for %s: %s", mmsi, exc)
    return {}
