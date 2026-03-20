"""Formal ontology layer for cross-source entity resolution and data fusion.

Provides:
- Entity type hierarchy (IS_A taxonomy tree)
- Cross-source field mappings (payload field -> canonical field)
- Equivalence resolution (fuzzy + taxonomic + spatial + ID cross-ref)
- Country normalization (ISO 3166-1 alpha-2/alpha-3)
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from math import radians, sin, cos, sqrt, atan2
from typing import Any

# ---------------------------------------------------------------------------
# 1. Source Groups -- which sources cover the same domain
# ---------------------------------------------------------------------------

SPECIES_SOURCES = frozenset({
    "OBIS", "GBIF", "WoRMS", "FishBase", "SeaLifeBase",
    "EMODnet Biology", "BOLD", "Ocean Tracking Network",
})

REGION_SOURCES = frozenset({
    "Marine Regions", "WDPA", "NOAA MPA Inventory",
})

INFRASTRUCTURE_SOURCES = frozenset({
    "BOEM", "BOEM Offshore Wind", "Crown Estate UK",
    "OSPAR", "Marine Cadastre",
})

COUNTRY_SOURCES = frozenset({
    "IUU Fishing Index", "FAO FishStatJ", "Sea Around Us",
    "ICES SAG", "IATI", "Green Climate Fund", "USDA GATS",
    "World Bank WDI", "Eurostat", "OECD", "UNCTAD",
})


# ---------------------------------------------------------------------------
# 2. Entity Type Hierarchy -- parent-child IS_A relationships
# ---------------------------------------------------------------------------

# Maps child -> parent.  None = root.
TYPE_HIERARCHY: dict[str, str | None] = {
    # Root types
    "entity": None,

    # Biodiversity branch
    "biodiversity_entity": "entity",
    "species_observation": "biodiversity_entity",
    "taxon": "biodiversity_entity",
    "fish_stock": "biodiversity_entity",
    "ecosystem": "biodiversity_entity",

    # Geographic branch
    "geographic_entity": "entity",
    "country": "geographic_entity",
    "region": "geographic_entity",
    "marine_protected_area": "geographic_entity",
    "eez": "geographic_entity",

    # Infrastructure branch
    "infrastructure_entity": "entity",
    "infrastructure": "infrastructure_entity",
    "port": "infrastructure_entity",
    "platform": "infrastructure_entity",

    # Organizational branch
    "organizational_entity": "entity",
    "organization": "organizational_entity",
    "company": "organizational_entity",

    # Other
    "project": "entity",
    "contract": "entity",

    # Geological
    "geological_feature": "entity",
    "hydrothermal_vent": "geological_feature",
    "seamount": "geological_feature",
}


def get_ancestors(entity_type: str) -> list[str]:
    """Return list of ancestor types from child to root."""
    ancestors = []
    current = entity_type
    visited: set[str] = set()
    while current in TYPE_HIERARCHY and current not in visited:
        visited.add(current)
        parent = TYPE_HIERARCHY[current]
        if parent is not None:
            ancestors.append(parent)
            current = parent
        else:
            break
    return ancestors


def types_compatible(type_a: str, type_b: str) -> bool:
    """Check if two entity types could refer to the same real-world thing.

    Compatible if: same type, one is ancestor of the other, or they share
    a common non-root ancestor.
    """
    if type_a == type_b:
        return True

    ancestors_a = set(get_ancestors(type_a)) | {type_a}
    ancestors_b = set(get_ancestors(type_b)) | {type_b}

    # One is ancestor of the other
    if type_a in ancestors_b or type_b in ancestors_a:
        return True

    # Share a common ancestor that is not the root "entity"
    common = ancestors_a & ancestors_b - {"entity"}
    return len(common) > 0


# ---------------------------------------------------------------------------
# 3. Cross-Source Field Mapping -- payload field -> canonical field name
# ---------------------------------------------------------------------------

# Maps (source_name, payload_field) -> canonical_field
# Used to extract comparable values from different source payloads.

CANONICAL_SPECIES_NAME: dict[str, str] = {
    "OBIS": "scientific_name",
    "GBIF": "species",
    "WoRMS": "scientificname",
    "FishBase": "Species",
    "SeaLifeBase": "Species",
    "EMODnet Biology": "scientific_name",
    "BOLD": "species_name",
    "Ocean Tracking Network": "scientificname",
}

CANONICAL_ENTITY_NAME: dict[str, list[str]] = {
    # source_name -> list of payload fields to try (first non-null wins)
    "OBIS": ["scientific_name", "vernacular_name"],
    "GBIF": ["species", "vernacularName"],
    "WoRMS": ["scientificname", "authority"],
    "FishBase": ["Species", "CommonName"],
    "SeaLifeBase": ["Species", "CommonName"],
    "Marine Regions": ["preferredGazetteerName", "placeName"],
    "WDPA": ["NAME", "ORIG_NAME"],
    "NOAA MPA Inventory": ["SITE_NAME", "Site_Name"],
    "BOEM": ["lease_number", "area_name"],
    "Crown Estate UK": ["name", "project_name"],
    "OSPAR": ["name", "installation_name"],
    "IUU Fishing Index": ["country_name"],
    "FAO FishStatJ": ["country"],
    "Sea Around Us": ["entity_name"],
    "IATI": ["title", "reporting_org"],
    "Green Climate Fund": ["title", "entity"],
}

# Cross-source identifier mappings -- which payload field holds a cross-ref ID
CROSS_REF_IDS: dict[str, dict[str, str]] = {
    # source_name -> {id_system: payload_field}
    "OBIS": {"aphia_id": "aphiaID", "gbif_id": "gbifID"},
    "GBIF": {"gbif_id": "key", "aphia_id": "worms_id"},
    "WoRMS": {"aphia_id": "AphiaID"},
    "FishBase": {"fishbase_id": "SpecCode", "aphia_id": "WoRMS_ID"},
    "Marine Regions": {"mrgid": "MRGID"},
    "WDPA": {"wdpa_id": "WDPAID"},
    "IUU Fishing Index": {"iso_a2": "country_code", "iso_a3": "country_code_a3"},
}


def extract_canonical_name(source_name: str, payload: dict) -> str | None:
    """Extract the best name for an entity from its source-specific payload."""
    fields = CANONICAL_ENTITY_NAME.get(source_name, [])
    for f in fields:
        val = payload.get(f)
        if val and str(val).strip():
            return str(val).strip()
    # Fallback: try common field names
    for f in ("name", "Name", "title", "label"):
        val = payload.get(f)
        if val and str(val).strip():
            return str(val).strip()
    return None


def extract_species_name(source_name: str, payload: dict) -> str | None:
    """Extract scientific species name from source-specific payload."""
    field = CANONICAL_SPECIES_NAME.get(source_name)
    if field:
        val = payload.get(field)
        if val and str(val).strip():
            return str(val).strip()
    return None


def extract_cross_ref_ids(source_name: str, payload: dict) -> dict[str, str]:
    """Extract cross-reference IDs from payload for matching across sources."""
    result: dict[str, str] = {}
    id_map = CROSS_REF_IDS.get(source_name, {})
    for id_system, field in id_map.items():
        val = payload.get(field)
        if val is not None and str(val).strip():
            result[id_system] = str(val).strip()
    return result


# ---------------------------------------------------------------------------
# 4. Equivalence Resolution
# ---------------------------------------------------------------------------

_STRIP_RE = re.compile(r"[^a-z0-9\s]")
_GENUS_SPECIES_RE = re.compile(r"^([A-Z][a-z]+)\s+([a-z]+)")


def _normalize(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    name = name.lower().strip()
    name = _STRIP_RE.sub("", name)
    return " ".join(name.split())


def _name_similarity(a: str, b: str) -> float:
    """Fuzzy name similarity 0.0-1.0."""
    na, nb = _normalize(a), _normalize(b)
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def _extract_genus_species(name: str) -> tuple[str, str] | None:
    """Extract (genus, species) from a binomial name like 'Rhincodon typus'."""
    m = _GENUS_SPECIES_RE.match(name.strip())
    if m:
        return (m.group(1).lower(), m.group(2).lower())
    return None


def _taxonomic_similarity(a: str, b: str) -> float:
    """Score taxonomic match: 1.0 for same binomial, 0.5 for same genus, 0.0 otherwise."""
    pa, pb = _extract_genus_species(a), _extract_genus_species(b)
    if pa is None or pb is None:
        return 0.0
    if pa == pb:
        return 1.0
    if pa[0] == pb[0]:
        return 0.5
    return 0.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two points."""
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _extract_coords(entity: dict) -> tuple[float, float] | None:
    """Extract (lat, lon) from entity geometry or payload."""
    geom = entity.get("geometry")
    if geom and isinstance(geom, dict):
        coords = geom.get("coordinates")
        if coords and isinstance(coords, (list, tuple)) and len(coords) >= 2:
            return (coords[1], coords[0])  # GeoJSON is [lon, lat]
    # Fallback: check payload
    payload = entity.get("payload") or {}
    lat = payload.get("latitude") or payload.get("lat") or payload.get("decimalLatitude")
    lon = payload.get("longitude") or payload.get("lon") or payload.get("lng") or payload.get("decimalLongitude")
    if lat is not None and lon is not None:
        try:
            return (float(lat), float(lon))
        except (ValueError, TypeError):
            return None
    return None


def _spatial_proximity(a: dict, b: dict, max_km: float = 5.0) -> float:
    """Score spatial proximity 0.0-1.0. Returns 1.0 if within tolerance, decays linearly."""
    ca, cb = _extract_coords(a), _extract_coords(b)
    if ca is None or cb is None:
        return 0.0
    dist = _haversine_km(ca[0], ca[1], cb[0], cb[1])
    if dist <= max_km:
        return 1.0
    if dist <= max_km * 5:
        return max(0.0, 1.0 - (dist - max_km) / (max_km * 4))
    return 0.0


def _cross_ref_match(a: dict, b: dict) -> float:
    """Score cross-reference ID match. Returns 1.0 if any shared cross-ref ID matches."""
    a_payload = a.get("payload") or {}
    b_payload = b.get("payload") or {}
    a_src = a.get("source_name", "")
    b_src = b.get("source_name", "")

    a_ids = extract_cross_ref_ids(a_src, a_payload)
    b_ids = extract_cross_ref_ids(b_src, b_payload)

    if not a_ids or not b_ids:
        return 0.0

    for id_system, a_val in a_ids.items():
        b_val = b_ids.get(id_system)
        if b_val and a_val == b_val:
            return 1.0

    return 0.0


def find_equivalent_entities(
    entity: dict,
    candidates: list[dict],
    *,
    spatial_km: float = 5.0,
) -> list[tuple[dict, float]]:
    """Score each candidate for equivalence with entity. Returns (candidate, confidence).

    Combines multiple signals:
    - Name matching (fuzzy + exact, case-insensitive)
    - Taxonomic matching (genus+species extraction)
    - Spatial proximity (same coords +/- tolerance)
    - Source-specific ID cross-ref (e.g. AphiaID from WoRMS maps to OBIS taxon)
    - Type compatibility check

    Returns list of (candidate, confidence) sorted by confidence descending.
    Only includes candidates with confidence > 0.3.
    """
    entity_name = entity.get("name", "")
    entity_type = entity.get("entity_type", "")
    results: list[tuple[dict, float]] = []

    for cand in candidates:
        cand_name = cand.get("name", "")
        cand_type = cand.get("entity_type", "")

        # Skip if same source (already deduped by UUID within source)
        if entity.get("source_name") == cand.get("source_name"):
            continue

        # Check type compatibility
        if entity_type and cand_type and not types_compatible(entity_type, cand_type):
            continue

        scores: dict[str, float] = {}

        # 1. Cross-ref ID match (strongest signal)
        xref = _cross_ref_match(entity, cand)
        if xref > 0:
            scores["cross_ref"] = xref

        # 2. Name similarity
        if entity_name and cand_name:
            name_score = _name_similarity(entity_name, cand_name)
            if name_score > 0.5:
                scores["name"] = name_score

        # 3. Taxonomic match (for species)
        if entity_name and cand_name:
            tax_score = _taxonomic_similarity(entity_name, cand_name)
            if tax_score > 0:
                scores["taxonomic"] = tax_score

        # 4. Spatial proximity
        spatial = _spatial_proximity(entity, cand, max_km=spatial_km)
        if spatial > 0:
            scores["spatial"] = spatial

        if not scores:
            continue

        # Weighted combination
        weights = {"cross_ref": 0.40, "name": 0.30, "taxonomic": 0.15, "spatial": 0.15}
        total_weight = sum(weights[k] for k in scores)
        if total_weight == 0:
            continue

        confidence = sum(scores[k] * weights[k] for k in scores) / total_weight

        # Boost: cross-ref + name match together = very high confidence
        if "cross_ref" in scores and "name" in scores and scores["name"] > 0.8:
            confidence = min(1.0, confidence * 1.15)

        # Boost: exact type match
        if entity_type == cand_type:
            confidence = min(1.0, confidence * 1.05)

        if confidence > 0.3:
            results.append((cand, round(confidence, 4)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


# ---------------------------------------------------------------------------
# 5. Country Normalization -- ISO 3166-1
# ---------------------------------------------------------------------------

# alpha-2 -> canonical name
_ISO_ALPHA2: dict[str, str] = {
    "AF": "Afghanistan", "AL": "Albania", "DZ": "Algeria", "AO": "Angola",
    "AR": "Argentina", "AU": "Australia", "AT": "Austria", "AZ": "Azerbaijan",
    "BS": "Bahamas", "BH": "Bahrain", "BD": "Bangladesh", "BB": "Barbados",
    "BY": "Belarus", "BE": "Belgium", "BZ": "Belize", "BJ": "Benin",
    "BO": "Bolivia", "BR": "Brazil", "BN": "Brunei", "BG": "Bulgaria",
    "BF": "Burkina Faso", "BI": "Burundi", "KH": "Cambodia", "CM": "Cameroon",
    "CA": "Canada", "CL": "Chile", "CN": "China", "CO": "Colombia",
    "CD": "Congo DR", "CG": "Congo", "CR": "Costa Rica", "CI": "Cote d'Ivoire",
    "HR": "Croatia", "CU": "Cuba", "CY": "Cyprus", "CZ": "Czechia",
    "DK": "Denmark", "DJ": "Djibouti", "DO": "Dominican Republic", "EC": "Ecuador",
    "EG": "Egypt", "SV": "El Salvador", "GQ": "Equatorial Guinea", "ER": "Eritrea",
    "EE": "Estonia", "SZ": "Eswatini", "ET": "Ethiopia", "FJ": "Fiji",
    "FI": "Finland", "FR": "France", "GA": "Gabon", "GM": "Gambia",
    "GE": "Georgia", "DE": "Germany", "GH": "Ghana", "GR": "Greece",
    "GT": "Guatemala", "GN": "Guinea", "GY": "Guyana", "HT": "Haiti",
    "HN": "Honduras", "HU": "Hungary", "IS": "Iceland", "IN": "India",
    "ID": "Indonesia", "IR": "Iran", "IQ": "Iraq", "IE": "Ireland",
    "IL": "Israel", "IT": "Italy", "JM": "Jamaica", "JP": "Japan",
    "JO": "Jordan", "KZ": "Kazakhstan", "KE": "Kenya", "KR": "South Korea",
    "KW": "Kuwait", "KG": "Kyrgyzstan", "LA": "Laos", "LV": "Latvia",
    "LB": "Lebanon", "LR": "Liberia", "LY": "Libya", "LT": "Lithuania",
    "LU": "Luxembourg", "MG": "Madagascar", "MW": "Malawi", "MY": "Malaysia",
    "MV": "Maldives", "ML": "Mali", "MT": "Malta", "MR": "Mauritania",
    "MU": "Mauritius", "MX": "Mexico", "MD": "Moldova", "MN": "Mongolia",
    "ME": "Montenegro", "MA": "Morocco", "MZ": "Mozambique", "MM": "Myanmar",
    "NA": "Namibia", "NP": "Nepal", "NL": "Netherlands", "NZ": "New Zealand",
    "NI": "Nicaragua", "NE": "Niger", "NG": "Nigeria", "KP": "North Korea",
    "MK": "North Macedonia", "NO": "Norway", "OM": "Oman", "PK": "Pakistan",
    "PA": "Panama", "PG": "Papua New Guinea", "PY": "Paraguay", "PE": "Peru",
    "PH": "Philippines", "PL": "Poland", "PT": "Portugal", "QA": "Qatar",
    "RO": "Romania", "RU": "Russia", "RW": "Rwanda", "SA": "Saudi Arabia",
    "SN": "Senegal", "RS": "Serbia", "SC": "Seychelles", "SL": "Sierra Leone",
    "SG": "Singapore", "SK": "Slovakia", "SI": "Slovenia", "SB": "Solomon Islands",
    "SO": "Somalia", "ZA": "South Africa", "ES": "Spain", "LK": "Sri Lanka",
    "SD": "Sudan", "SR": "Suriname", "SE": "Sweden", "CH": "Switzerland",
    "SY": "Syria", "TW": "Taiwan", "TZ": "Tanzania", "TH": "Thailand",
    "TL": "Timor-Leste", "TG": "Togo", "TO": "Tonga", "TT": "Trinidad and Tobago",
    "TN": "Tunisia", "TR": "Turkey", "TM": "Turkmenistan", "UG": "Uganda",
    "UA": "Ukraine", "AE": "United Arab Emirates", "GB": "United Kingdom",
    "US": "United States", "UY": "Uruguay", "UZ": "Uzbekistan", "VU": "Vanuatu",
    "VE": "Venezuela", "VN": "Vietnam", "YE": "Yemen", "ZM": "Zambia",
    "ZW": "Zimbabwe",
    # Territories / small states relevant to ocean data
    "AS": "American Samoa", "GU": "Guam", "PR": "Puerto Rico",
    "VI": "US Virgin Islands", "FK": "Falkland Islands", "GI": "Gibraltar",
    "GL": "Greenland", "FO": "Faroe Islands", "BM": "Bermuda",
    "KY": "Cayman Islands", "PF": "French Polynesia", "NC": "New Caledonia",
    "WS": "Samoa", "MH": "Marshall Islands", "FM": "Micronesia",
    "PW": "Palau", "NR": "Nauru", "TV": "Tuvalu", "KI": "Kiribati",
}

# alpha-3 -> alpha-2
_ISO_ALPHA3_TO_2: dict[str, str] = {
    "AFG": "AF", "ALB": "AL", "DZA": "DZ", "AGO": "AO", "ARG": "AR",
    "AUS": "AU", "AUT": "AT", "AZE": "AZ", "BHS": "BS", "BHR": "BH",
    "BGD": "BD", "BRB": "BB", "BLR": "BY", "BEL": "BE", "BLZ": "BZ",
    "BEN": "BJ", "BOL": "BO", "BRA": "BR", "BRN": "BN", "BGR": "BG",
    "BFA": "BF", "BDI": "BI", "KHM": "KH", "CMR": "CM", "CAN": "CA",
    "CHL": "CL", "CHN": "CN", "COL": "CO", "COD": "CD", "COG": "CG",
    "CRI": "CR", "CIV": "CI", "HRV": "HR", "CUB": "CU", "CYP": "CY",
    "CZE": "CZ", "DNK": "DK", "DJI": "DJ", "DOM": "DO", "ECU": "EC",
    "EGY": "EG", "SLV": "SV", "GNQ": "GQ", "ERI": "ER", "EST": "EE",
    "SWZ": "SZ", "ETH": "ET", "FJI": "FJ", "FIN": "FI", "FRA": "FR",
    "GAB": "GA", "GMB": "GM", "GEO": "GE", "DEU": "DE", "GHA": "GH",
    "GRC": "GR", "GTM": "GT", "GIN": "GN", "GUY": "GY", "HTI": "HT",
    "HND": "HN", "HUN": "HU", "ISL": "IS", "IND": "IN", "IDN": "ID",
    "IRN": "IR", "IRQ": "IQ", "IRL": "IE", "ISR": "IL", "ITA": "IT",
    "JAM": "JM", "JPN": "JP", "JOR": "JO", "KAZ": "KZ", "KEN": "KE",
    "KOR": "KR", "KWT": "KW", "KGZ": "KG", "LAO": "LA", "LVA": "LV",
    "LBN": "LB", "LBR": "LR", "LBY": "LY", "LTU": "LT", "LUX": "LU",
    "MDG": "MG", "MWI": "MW", "MYS": "MY", "MDV": "MV", "MLI": "ML",
    "MLT": "MT", "MRT": "MR", "MUS": "MU", "MEX": "MX", "MDA": "MD",
    "MNG": "MN", "MNE": "ME", "MAR": "MA", "MOZ": "MZ", "MMR": "MM",
    "NAM": "NA", "NPL": "NP", "NLD": "NL", "NZL": "NZ", "NIC": "NI",
    "NER": "NE", "NGA": "NG", "PRK": "KP", "MKD": "MK", "NOR": "NO",
    "OMN": "OM", "PAK": "PK", "PAN": "PA", "PNG": "PG", "PRY": "PY",
    "PER": "PE", "PHL": "PH", "POL": "PL", "PRT": "PT", "QAT": "QA",
    "ROU": "RO", "RUS": "RU", "RWA": "RW", "SAU": "SA", "SEN": "SN",
    "SRB": "RS", "SYC": "SC", "SLE": "SL", "SGP": "SG", "SVK": "SK",
    "SVN": "SI", "SLB": "SB", "SOM": "SO", "ZAF": "ZA", "ESP": "ES",
    "LKA": "LK", "SDN": "SD", "SUR": "SR", "SWE": "SE", "CHE": "CH",
    "SYR": "SY", "TWN": "TW", "TZA": "TZ", "THA": "TH", "TLS": "TL",
    "TGO": "TG", "TON": "TO", "TTO": "TT", "TUN": "TN", "TUR": "TR",
    "TKM": "TM", "UGA": "UG", "UKR": "UA", "ARE": "AE", "GBR": "GB",
    "USA": "US", "URY": "UY", "UZB": "UZ", "VUT": "VU", "VEN": "VE",
    "VNM": "VN", "YEM": "YE", "ZMB": "ZM", "ZWE": "ZW",
}

# Common name variations -> alpha-2
_COUNTRY_ALIASES: dict[str, str] = {
    "united states of america": "US",
    "united states": "US",
    "usa": "US",
    "u.s.a.": "US",
    "u.s.": "US",
    "united kingdom": "GB",
    "great britain": "GB",
    "uk": "GB",
    "u.k.": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
    "people's republic of china": "CN",
    "china": "CN",
    "republic of korea": "KR",
    "south korea": "KR",
    "korea, republic of": "KR",
    "democratic people's republic of korea": "KP",
    "north korea": "KP",
    "korea, dem. people's rep.": "KP",
    "russian federation": "RU",
    "russia": "RU",
    "iran, islamic republic of": "IR",
    "iran": "IR",
    "venezuela, bolivarian republic of": "VE",
    "venezuela": "VE",
    "tanzania, united republic of": "TZ",
    "tanzania": "TZ",
    "viet nam": "VN",
    "vietnam": "VN",
    "bolivia, plurinational state of": "BO",
    "bolivia": "BO",
    "democratic republic of the congo": "CD",
    "congo, dem. rep.": "CD",
    "dr congo": "CD",
    "drc": "CD",
    "republic of the congo": "CG",
    "congo": "CG",
    "cote divoire": "CI",
    "ivory coast": "CI",
    "czech republic": "CZ",
    "czechia": "CZ",
    "turkiye": "TR",
    "turkey": "TR",
    "eswatini": "SZ",
    "swaziland": "SZ",
    "myanmar": "MM",
    "burma": "MM",
    "timor leste": "TL",
    "east timor": "TL",
    "cabo verde": "CV",
    "cape verde": "CV",
    "the netherlands": "NL",
    "holland": "NL",
    "new zealand": "NZ",
    "aotearoa": "NZ",
    "south africa": "ZA",
    "uae": "AE",
    "united arab emirates": "AE",
    "saudi arabia": "SA",
    "ksa": "SA",
    "philippines": "PH",
    "the philippines": "PH",
    "trinidad & tobago": "TT",
    "trinidad and tobago": "TT",
    "north macedonia": "MK",
    "the gambia": "GM",
    "gambia": "GM",
    "papua new guinea": "PG",
    "png": "PG",
}

# Build reverse lookup: canonical name -> alpha-2
_NAME_TO_ALPHA2: dict[str, str] = {}
for _code, _name in _ISO_ALPHA2.items():
    _NAME_TO_ALPHA2[_name.lower()] = _code


def normalize_country(raw: str | None) -> str | None:
    """Normalize a country string to ISO 3166-1 alpha-2 code.

    Handles: alpha-2, alpha-3, full names, and common variations.
    Returns None if unrecognizable.
    """
    if not raw or not raw.strip():
        return None

    raw = raw.strip()

    # Already alpha-2?
    if len(raw) == 2 and raw.upper() in _ISO_ALPHA2:
        return raw.upper()

    # Alpha-3?
    if len(raw) == 3 and raw.upper() in _ISO_ALPHA3_TO_2:
        return _ISO_ALPHA3_TO_2[raw.upper()]

    # Normalize for lookup
    lower = raw.lower().strip()

    # Check aliases
    if lower in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[lower]

    # Check canonical names
    if lower in _NAME_TO_ALPHA2:
        return _NAME_TO_ALPHA2[lower]

    # Strip common prefixes/suffixes
    for prefix in ("the ", "republic of ", "state of "):
        if lower.startswith(prefix):
            trimmed = lower[len(prefix):]
            if trimmed in _NAME_TO_ALPHA2:
                return _NAME_TO_ALPHA2[trimmed]
            if trimmed in _COUNTRY_ALIASES:
                return _COUNTRY_ALIASES[trimmed]

    return None


def country_name(code: str) -> str | None:
    """Get canonical country name from alpha-2 code."""
    return _ISO_ALPHA2.get(code.upper()) if code else None
