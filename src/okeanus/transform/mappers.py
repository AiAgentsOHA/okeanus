"""30 mapper functions -- one per blue economy adapter source_name."""

from __future__ import annotations

from okeanus.transform.pipeline import (
    TransformResult,
    entity_uuid,
    register_mapper,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base(rec: dict) -> dict:
    """Extract common fields present on every adapter output record."""
    return {
        "source_name": rec.get("source_name"),
        "source_id": rec.get("source_id", ""),
        "quality_score": rec.get("quality_score"),
        "geometry": rec.get("geometry"),
        "timestamp": rec.get("timestamp"),
    }


def _ts(rec: dict, *, code: str, name: str | None = None, value: float,
        unit: str | None = None, commodity: str | None = None,
        country: str | None = None, payload: dict | None = None) -> dict:
    """Build a time_series dict."""
    b = _base(rec)
    b.update(code=code, name=name, value=value, unit=unit,
             commodity=commodity, country=country, payload=payload)
    return b


# ===================================================================
# Phase 1 -- Government Stats (8 mappers, all TimeSeries-only)
# ===================================================================


@register_mapper("World Bank WDI")
def _world_bank(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("value") is None:
            continue
        ts.append(_ts(rec, code=p["indicator_code"], name=p.get("indicator_name"),
                       value=p["value"], unit=p.get("unit"), country=p.get("country_code"),
                       payload=p))
    return TransformResult(time_series=ts)


@register_mapper("FRED")
def _fred(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("value") is None:
            continue
        ts.append(_ts(rec, code=p["series_id"], name=p.get("series_name"),
                       value=p["value"], payload=p))
    return TransformResult(time_series=ts)


@register_mapper("NOAA ENOW")
def _noaa_enow(records: list[dict]) -> TransformResult:
    ts = []
    metrics = [("gdp", "USD"), ("employment", "jobs"), ("wages", "USD"), ("establishments", "count")]
    for rec in records:
        p = rec.get("payload", {})
        sector = p.get("sector", "unknown")
        for metric_name, metric_unit in metrics:
            val = p.get(metric_name)
            if val is None:
                continue
            ts.append(_ts(rec, code=f"enow-{sector}-{metric_name}",
                          name=f"{sector} {metric_name}", value=val,
                          unit=metric_unit, country="US", payload=p))
    return TransformResult(time_series=ts)


@register_mapper("Eurostat")
def _eurostat(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("value") is None:
            continue
        ts.append(_ts(rec, code=p["dataset"], name=p.get("dataset_name"),
                       value=p["value"], country=p.get("country_code"), payload=p))
    return TransformResult(time_series=ts)


@register_mapper("UNCTAD", "UNCTAD via UNdata")
def _unctad(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("value") is None:
            continue
        ts.append(_ts(rec, code=p["indicator"], name=p.get("indicator_name"),
                       value=p["value"], unit=p.get("unit"),
                       country=p.get("country"), payload=p))
    return TransformResult(time_series=ts)


@register_mapper("IMF PCPS")
def _imf_pcps(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("value") is None:
            continue
        ts.append(_ts(rec, code=p["commodity_code"], name=p.get("commodity_name"),
                       value=p["value"], unit=p.get("unit", "index"),
                       commodity=p.get("commodity_name"), payload=p))
    return TransformResult(time_series=ts)


@register_mapper("ILO ILOSTAT")
def _ilo(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("value") is None:
            continue
        ts.append(_ts(rec, code=p["indicator"], name=p.get("sector_name"),
                       value=p["value"], country=p.get("country"), payload=p))
    return TransformResult(time_series=ts)


@register_mapper("OECD")
def _oecd(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("value") is None:
            continue
        ts.append(_ts(rec, code=p["dataset"], name=p.get("dataset_name"),
                       value=p["value"], country=p.get("country"), payload=p))
    return TransformResult(time_series=ts)


# ===================================================================
# Phase 2 -- Trader Layer (8 mappers)
# ===================================================================


@register_mapper("SSB Norway")
def _ssb(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("value") is None:
            continue
        ts.append(_ts(rec, code=p["table"], name=p.get("table_name"),
                       value=p["value"], commodity="salmon", country="NO", payload=p))
    return TransformResult(time_series=ts)


@register_mapper("EUMOFA")
def _eumofa(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("price") is None:
            continue
        ts.append(_ts(rec, code=p["category"], name=p.get("category_name"),
                       value=p["price"], unit=p.get("unit", "EUR/kg"),
                       commodity=p.get("species"), country=p.get("country"), payload=p))
    return TransformResult(time_series=ts)


@register_mapper("USDA GATS")
def _usda_gats(records: list[dict]) -> TransformResult:
    ts, flows, entities = [], [], []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("value_usd") is None:
            continue
        b = _base(rec)

        # Create source entity (US)
        us_id = entity_uuid("USDA GATS", "country-US")
        us_ent = dict(b)
        us_ent.update(id=us_id, entity_type="country", name="United States",
                      source_id=str(us_id), identifier="US", country="US",
                      sector="trade", status=None, payload=None)
        entities.append(us_ent)

        # Create partner entity
        partner = p.get("partner_name", "unknown")
        partner_id = entity_uuid("USDA GATS", f"country-{partner}")
        partner_ent = dict(b)
        partner_ent.update(id=partner_id, entity_type="country", name=partner,
                          source_id=str(partner_id), identifier=partner,
                          country=p.get("partner_code"), sector="trade",
                          status=None, payload=None)
        entities.append(partner_ent)

        ts.append(_ts(rec, code=f"gats-{p['hs_code']}", name=p.get("commodity"),
                       value=p["value_usd"], unit="USD",
                       commodity=p.get("commodity"), country=p.get("partner_name"),
                       payload=p))

        # Determine flow direction
        flow_dir = p.get("flow", "export")
        src_id = us_id if flow_dir.lower() in ("export", "re-export") else partner_id
        dst_id = partner_id if flow_dir.lower() in ("export", "re-export") else us_id

        flow = dict(b)
        flow.update(flow_type=p["flow"], amount=p["value_usd"], currency="USD",
                    commodity=p.get("commodity"), purpose=None,
                    source_entity_id=src_id, dest_entity_id=dst_id, payload=p)
        flows.append(flow)
    return TransformResult(time_series=ts, flows=flows, entities=entities)


@register_mapper("NOAA FOSS")
def _noaa_foss(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        rec_type = p.get("type")
        if rec_type == "landings":
            if p.get("dollars") is None:
                continue
            ts.append(_ts(rec, code=f"foss-landings-{p['species']}",
                          name=p.get("species"), value=p["dollars"],
                          unit="USD", commodity=p.get("species"), country="US", payload=p))
        elif rec_type == "foreign_trade":
            if p.get("dollars") is None:
                continue
            ts.append(_ts(rec, code=f"foss-trade-{p['product']}",
                          name=p.get("product"), value=p["dollars"],
                          unit="USD", commodity=p.get("product"),
                          country=p.get("country"), payload=p))
    return TransformResult(time_series=ts)


@register_mapper("Shanghai Shipping Exchange")
def _shanghai(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("value") is None:
            continue
        ts.append(_ts(rec, code=p["index_code"], name=p.get("index_name"),
                       value=p["value"], unit="index", country="CN", payload=p))
    return TransformResult(time_series=ts)


@register_mapper("Bunker Index")
def _bunker(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("price_usd_mt") is None:
            continue
        ts.append(_ts(rec, code=p["fuel_type"], name=p.get("fuel_name"),
                       value=p["price_usd_mt"], unit="USD/mt",
                       commodity=p.get("fuel_name"), payload=p))
    return TransformResult(time_series=ts)


@register_mapper("OilPriceAPI")
def _oilprice(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("price_usd") is None:
            continue
        ts.append(_ts(rec, code=p["product_code"], name=p.get("product_name"),
                       value=p["price_usd"], unit=p.get("unit", "per barrel"),
                       commodity=p.get("product_name"), payload=p))
    return TransformResult(time_series=ts)


@register_mapper("USDA AgTransport")
def _usda_ag(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        if p.get("price_usd") is None:
            continue
        ts.append(_ts(rec, code=f"usda-bunker-{p['fuel_type']}",
                       name=p.get("fuel_type"), value=p["price_usd"],
                       unit=p.get("unit", "USD/mt"), commodity=p.get("fuel_type"),
                       country="US", payload=p))
    return TransformResult(time_series=ts)


# ===================================================================
# Phase 3 -- Finance (4 mappers)
# ===================================================================


@register_mapper("IATI")
def _iati(records: list[dict]) -> TransformResult:
    entities, flows = [], []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        org = p.get("reporting_org", "unknown")
        eid = entity_uuid("IATI", f"org-{org}")

        rc = p.get("recipient_country")
        sc = p.get("sector_codes")

        ent = dict(b)
        ent.update(id=eid, entity_type="organization", name=org,
                   source_id=str(eid),
                   identifier=p.get("iati_identifier"),
                   country=rc[0] if isinstance(rc, list) and rc else None,
                   sector=sc[0] if isinstance(sc, list) and sc else None,
                   status=p.get("status"), payload=p)
        entities.append(ent)

        # Create recipient country entity
        dest_id = None
        if rc:
            rc_name = rc[0] if isinstance(rc, list) and rc else rc
            if rc_name:
                dest_id = entity_uuid("IATI", f"country-{rc_name}")
                dest_ent = dict(b)
                dest_ent.update(id=dest_id, entity_type="country", name=rc_name,
                              source_id=str(dest_id), identifier=rc_name,
                              country=rc_name, sector="development",
                              status=None, payload=None)
                entities.append(dest_ent)

        if p.get("total_value") is not None:
            flow = dict(b)
            flow.update(flow_type="development_aid", amount=p["total_value"],
                        currency=p.get("currency", "USD"), commodity=None,
                        purpose=p.get("title"), source_entity_id=eid,
                        dest_entity_id=dest_id, payload=p)
            flows.append(flow)

    return TransformResult(entities=entities, flows=flows)


@register_mapper("Green Climate Fund")
def _gcf(records: list[dict]) -> TransformResult:
    entities, flows = [], []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        org = p.get("entity", "unknown")
        eid = entity_uuid("Green Climate Fund", f"org-{org}")

        country_raw = p.get("country")
        country = country_raw[0] if isinstance(country_raw, list) and country_raw else country_raw

        ent = dict(b)
        ent.update(id=eid, entity_type="organization", name=org,
                   source_id=str(eid),
                   country=country, sector=p.get("sector"),
                   status=p.get("status"), payload=p)
        entities.append(ent)

        # Create recipient country entity
        dest_id = None
        if country:
            dest_id = entity_uuid("Green Climate Fund", f"country-{country}")
            dest_ent = dict(b)
            dest_ent.update(id=dest_id, entity_type="country", name=country,
                          source_id=str(dest_id), identifier=country,
                          country=country, sector="climate",
                          status=None, payload=None)
            entities.append(dest_ent)

        if p.get("gcf_amount_usd") is not None:
            flow = dict(b)
            flow.update(flow_type="climate_finance", amount=p["gcf_amount_usd"],
                        currency="USD", commodity=None,
                        purpose=p.get("title"), source_entity_id=eid,
                        dest_entity_id=dest_id, payload=p)
            flows.append(flow)

    return TransformResult(entities=entities, flows=flows)


@register_mapper("Verra VCS / CAD Trust")
def _verra(records: list[dict]) -> TransformResult:
    entities, assessments = [], []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        pid = p.get("project_id", rec.get("source_id", "unknown"))
        eid = entity_uuid("Verra VCS / CAD Trust", f"project-{pid}")

        ent = dict(b)
        ent.update(id=eid, entity_type="project", name=p.get("name", str(pid)),
                   source_id=str(eid), identifier=str(pid),
                   country=p.get("country"), sector="carbon_credits",
                   status=p.get("status"), payload=p)
        entities.append(ent)

        for metric in ("credits_issued", "credits_retired", "credits_available"):
            val = p.get(metric)
            if val is None:
                continue
            a = dict(b)
            a.update(entity_id=eid, assessor="Verra", metric_code=metric,
                     score_numeric=val, score_category=None,
                     confidence=None, trend=None, payload=p)
            assessments.append(a)

    return TransformResult(entities=entities, assessments=assessments)


@register_mapper("WBA Seafood Stewardship Index")
def _wba(records: list[dict]) -> TransformResult:
    entities, assessments = [], []
    dims = [
        ("total_score", "seafood_total"),
        ("governance_score", "seafood_governance"),
        ("ecosystems_score", "seafood_ecosystems"),
        ("traceability_score", "seafood_traceability"),
        ("social_score", "seafood_social"),
    ]
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        company = p.get("company_name", "unknown")
        eid = entity_uuid("WBA Seafood Stewardship Index", f"company-{company}")

        ent = dict(b)
        ent.update(id=eid, entity_type="company", name=company,
                   source_id=str(eid), country=p.get("country"),
                   sector=p.get("sector"), status=None, payload=p)
        entities.append(ent)

        for score_key, metric_code in dims:
            val = p.get(score_key)
            if val is None:
                continue
            a = dict(b)
            cat = str(p.get("rank")) if score_key == "total_score" and p.get("rank") is not None else None
            a.update(entity_id=eid, assessor="WBA", metric_code=metric_code,
                     score_numeric=val, score_category=cat,
                     confidence=None, trend=None, payload=p)
            assessments.append(a)

    return TransformResult(entities=entities, assessments=assessments)


# ===================================================================
# Phase 4 -- Risk & Infrastructure (5 mappers)
# ===================================================================


@register_mapper("FEMA NFIP")
def _fema(records: list[dict]) -> TransformResult:
    ts, events = [], []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        rec_type = p.get("type")

        if rec_type == "flood_claim":
            ev = dict(b)
            ev.update(event_type="flood_claim",
                      name=f"NFIP flood claim {p.get('state', '')}",
                      description=p.get("cause_of_damage"),
                      severity=None,
                      economic_impact=p.get("total_paid"), payload=p)
            events.append(ev)

            if p.get("total_paid") is not None:
                ts.append(_ts(rec, code="nfip-claims",
                              name="NFIP Flood Claim Payout",
                              value=p["total_paid"], unit="USD",
                              country="US", payload=p))

        elif rec_type == "flood_policy":
            ev = dict(b)
            ev.update(event_type="flood_policy",
                      name=f"NFIP policy {p.get('state', '')}",
                      description=None, severity=None,
                      economic_impact=p.get("total_coverage"), payload=p)
            events.append(ev)

    return TransformResult(time_series=ts, events=events)


@register_mapper("BOEM")
def _boem(records: list[dict]) -> TransformResult:
    entities, relationships = [], []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        sid = rec.get("source_id", "unknown")
        layer = p.get("layer", "unknown")
        infra_key = f"{layer}-{p.get('lease_number', sid)}"
        infra_id = entity_uuid("BOEM", infra_key)

        ent = dict(b)
        ent.update(id=infra_id, entity_type="infrastructure",
                   name=p.get("lease_number") or p.get("area_name", sid),
                   source_id=str(infra_id),
                   identifier=p.get("lease_number"),
                   country="US", sector=layer,
                   status=p.get("status"), payload=p)
        entities.append(ent)

        company = p.get("company")
        if company:
            op_id = entity_uuid("BOEM", f"operator-{company}")
            op = dict(b)
            op.update(id=op_id, entity_type="company", name=company,
                      source_id=str(op_id), country="US", sector=layer,
                      status=None, payload=None)
            entities.append(op)

            rel = dict(b)
            rel.update(source_entity_id=op_id, dest_entity_id=infra_id,
                       relationship_type="operates", strength=None,
                       status=p.get("status"), payload=p)
            relationships.append(rel)

    return TransformResult(entities=entities, relationships=relationships)


@register_mapper("Crown Estate UK")
def _crown_estate(records: list[dict]) -> TransformResult:
    entities, relationships = [], []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        sid = rec.get("source_id", "unknown")
        layer = p.get("layer", "unknown")
        infra_key = f"{layer}-{p.get('name', sid)}"
        infra_id = entity_uuid("Crown Estate UK", infra_key)

        ent = dict(b)
        ent.update(id=infra_id, entity_type="infrastructure",
                   name=p.get("name", sid), source_id=str(infra_id),
                   country="GB", sector=layer,
                   status=p.get("status"), payload=p)
        entities.append(ent)

        operator = p.get("operator")
        if operator:
            op_id = entity_uuid("Crown Estate UK", f"operator-{operator}")
            op = dict(b)
            op.update(id=op_id, entity_type="company", name=operator,
                      source_id=str(op_id), country="GB", sector=layer,
                      status=None, payload=None)
            entities.append(op)

            rel = dict(b)
            rel.update(source_entity_id=op_id, dest_entity_id=infra_id,
                       relationship_type="operates", strength=None,
                       status=p.get("status"), payload=p)
            relationships.append(rel)

    return TransformResult(entities=entities, relationships=relationships)


@register_mapper("OSPAR")
def _ospar(records: list[dict]) -> TransformResult:
    entities, relationships = [], []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        sid = rec.get("source_id", "unknown")
        infra_key = f"installation-{p.get('name', sid)}"
        infra_id = entity_uuid("OSPAR", infra_key)

        ent = dict(b)
        ent.update(id=infra_id, entity_type="infrastructure",
                   name=p.get("name", sid), source_id=str(infra_id),
                   country=p.get("country"),
                   sector=p.get("type", "offshore_installation"),
                   status=p.get("status"), payload=p)
        entities.append(ent)

        operator = p.get("operator")
        if operator:
            op_id = entity_uuid("OSPAR", f"operator-{operator}")
            op = dict(b)
            op.update(id=op_id, entity_type="company", name=operator,
                      source_id=str(op_id), country=p.get("country"),
                      sector="offshore", status=None, payload=None)
            entities.append(op)

            rel = dict(b)
            rel.update(source_entity_id=op_id, dest_entity_id=infra_id,
                       relationship_type="operates", strength=None,
                       status=p.get("status"), payload=p)
            relationships.append(rel)

    return TransformResult(entities=entities, relationships=relationships)


@register_mapper("IUU Fishing Index")
def _iuu(records: list[dict]) -> TransformResult:
    entities, assessments = [], []
    dims = [
        ("overall_score", "iuu_overall"),
        ("coastal_score", "iuu_coastal"),
        ("flag_score", "iuu_flag"),
        ("port_score", "iuu_port"),
        ("market_score", "iuu_market"),
    ]
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        cc = p.get("country_code", "XX")
        eid = entity_uuid("IUU Fishing Index", f"country-{cc}")

        ent = dict(b)
        ent.update(id=eid, entity_type="country", name=p.get("country_name", cc),
                   source_id=str(eid), identifier=cc, country=cc,
                   sector=None, status=None, payload=p)
        entities.append(ent)

        for score_key, metric_code in dims:
            val = p.get(score_key)
            if val is None:
                continue
            a = dict(b)
            cat = str(p.get("rank")) if score_key == "overall_score" and p.get("rank") is not None else None
            a.update(entity_id=eid, assessor="IUU Fishing Index",
                     metric_code=metric_code, score_numeric=val,
                     score_category=cat, confidence=None, trend=None, payload=p)
            assessments.append(a)

    return TransformResult(entities=entities, assessments=assessments)


# ===================================================================
# Phase 5 -- Fisheries & Ecosystem (5 mappers)
# ===================================================================


@register_mapper("Sea Around Us")
def _sau(records: list[dict]) -> TransformResult:
    ts, flows, entities = [], [], []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        if p.get("value") is None:
            continue

        region_type = p.get("region_type", "unknown")
        dimension = p.get("dimension", "unknown")
        commodity = p.get("entity_name") if dimension in ("taxon", "commercialgroup") else None

        # Create entity for the fishing country/region
        entity_name = p.get("entity_name", "unknown")
        eid = None
        if dimension == "country":
            eid = entity_uuid("Sea Around Us", f"country-{entity_name}")
            ent = dict(b)
            ent.update(id=eid, entity_type="country", name=entity_name,
                      source_id=str(eid), identifier=entity_name,
                      country=None, sector="fisheries",
                      status=None, payload=None)
            entities.append(ent)

        ts.append(_ts(rec, code=f"sau-{region_type}-{dimension}",
                       name=entity_name, value=p["value"],
                       unit=p.get("unit"), commodity=commodity, payload=p))

        if dimension == "country":
            flow = dict(b)
            flow.update(flow_type="catch", amount=p["value"], currency=None,
                        unit=p.get("unit"), commodity=None,
                        purpose=f"{region_type} {p.get('measure', '')}",
                        source_entity_id=eid, dest_entity_id=None, payload=p)
            flows.append(flow)

    return TransformResult(time_series=ts, flows=flows, entities=entities)


@register_mapper("ICES SAG")
def _ices(records: list[dict]) -> TransformResult:
    ts, assessments, entities = [], [], []
    unit_map = {
        "ssb": "tonnes", "fishing_mortality": "F", "recruitment": "thousands",
        "catches": "tonnes", "landings": "tonnes", "discards": "tonnes",
    }
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        stock = p.get("stock_code", "unknown")

        # Create fish stock entity
        eid = entity_uuid("ICES SAG", f"stock-{stock}")
        ent = dict(b)
        ent.update(id=eid, entity_type="fish_stock", name=stock,
                   source_id=str(eid), identifier=stock,
                   country=p.get("ecoregion"), sector="fisheries",
                   status=p.get("stock_status"), payload=p)
        entities.append(ent)

        if "fishing_mortality" in p:
            # Stock detail record
            for metric in ("ssb", "fishing_mortality", "recruitment", "catches", "landings", "discards"):
                val = p.get(metric)
                if val is None:
                    continue
                ts.append(_ts(rec, code=f"ices-{stock}-{metric}",
                              name=f"{stock} {metric}", value=val,
                              unit=unit_map.get(metric), commodity=stock, payload=p))

            a = dict(b)
            a.update(entity_id=eid, assessor="ICES", metric_code="stock_status",
                     score_numeric=None, score_category=p.get("stock_status"),
                     confidence=None, trend=None, payload=p)
            assessments.append(a)
        else:
            # Summary record
            a = dict(b)
            a.update(entity_id=eid, assessor="ICES", metric_code="stock_advice",
                     score_numeric=None, score_category=p.get("advice_status"),
                     confidence=None, trend=None, payload=p)
            assessments.append(a)

    return TransformResult(time_series=ts, assessments=assessments, entities=entities)


@register_mapper("FAO FishStatJ")
def _fao(records: list[dict]) -> TransformResult:
    ts, flows, entities = [], [], []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        if p.get("value") is None:
            continue

        country = p.get("country")
        eid = None
        if country:
            eid = entity_uuid("FAO FishStatJ", f"country-{country}")
            ent = dict(b)
            ent.update(id=eid, entity_type="country", name=country,
                      source_id=str(eid), identifier=country,
                      country=country, sector="fisheries",
                      status=None, payload=None)
            entities.append(ent)

        name = p.get("species") or p.get("indicator_name") or p.get("dataset_name", "")
        ts.append(_ts(rec, code=f"fishstat-{p.get('dataset', 'unknown')}",
                       name=name, value=p["value"], unit=p.get("unit"),
                       commodity=p.get("species"), country=country, payload=p))

        if p.get("dataset") == "commodities":
            flow = dict(b)
            flow.update(flow_type="fish_trade", amount=p["value"], currency=None,
                        unit=p.get("unit"), commodity=p.get("species"),
                        purpose=None, source_entity_id=eid,
                        dest_entity_id=None, payload=p)
            flows.append(flow)

    return TransformResult(time_series=ts, flows=flows, entities=entities)


@register_mapper("ESVD")
def _esvd(records: list[dict]) -> TransformResult:
    assessments, entities = [], []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)

        biome = p.get("biome", "unknown")
        eid = entity_uuid("ESVD", f"biome-{biome}")
        ent = dict(b)
        ent.update(id=eid, entity_type="ecosystem", name=biome,
                   source_id=str(eid), identifier=biome,
                   country=p.get("country"), sector="ecosystem_services",
                   status=None, payload=p)
        entities.append(ent)

        a = dict(b)
        a.update(entity_id=eid, assessor="ESVD",
                 metric_code=p.get("service_type", "unknown"),
                 score_numeric=p.get("value_per_ha_year"),
                 score_category=p.get("confidence"),
                 confidence=None, trend=None, payload=p)
        assessments.append(a)
    return TransformResult(assessments=assessments, entities=entities)


@register_mapper("ISA DeepData")
def _isa(records: list[dict]) -> TransformResult:
    entities, relationships = [], []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        sid = rec.get("source_id", "unknown")
        area = p.get("area_name", sid)
        contract_id = entity_uuid("ISA DeepData", f"contract-{area}")

        ent = dict(b)
        ent.update(id=contract_id, entity_type="contract", name=area,
                   source_id=str(contract_id), identifier=sid,
                   country=p.get("sponsoring_state"),
                   sector=p.get("mineral_type"),
                   status=p.get("status"), payload=p)
        entities.append(ent)

        contractor = p.get("contractor")
        if contractor:
            con_id = entity_uuid("ISA DeepData", f"contractor-{contractor}")
            con = dict(b)
            con.update(id=con_id, entity_type="company", name=contractor,
                       source_id=str(con_id),
                       country=p.get("sponsoring_state"),
                       sector="deep_sea_mining", status=None, payload=None)
            entities.append(con)

            rel = dict(b)
            rel.update(source_entity_id=con_id, dest_entity_id=contract_id,
                       relationship_type="contractor", strength=None,
                       status=p.get("status"), payload=p)
            relationships.append(rel)

    return TransformResult(entities=entities, relationships=relationships)
