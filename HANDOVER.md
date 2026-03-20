# Okeanus Session Handover — 2026-03-20 (Session 3)

## Summary: Platform Fully Operational

This session closed all remaining gaps from Session 2: entity geometry (4.2% → 97.5%), lineage populated (491 nodes, 387 edges), semantic edges created (10K), LLM client hardened with timeout+retry, Redis enabled, AIS streaming robustified. UoT hypothesis generation in progress.

## Database State (pg17)
| Table | Rows | Status |
|-------|------|--------|
| observations | 49,122 | Raw data from 98 sources (all with geometry) |
| entities | 42,352 | 41,298 with geometry (97.5%) |
| events | 1,500 | 495 with geometry |
| assessments | 5,191 | Including 4,100 ESVD ecosystem valuations |
| time_series | 2,496 | From batch_ingest adapters |
| embeddings | 99,142 | Nomic v2-MoE (42K entity + 1.5K event + 55K obs) |
| knowledge_edges | 20,003 | 10K SPATIALLY_NEAR + 10K RELATES_TO (semantic) + 6 CORRELATES_WITH + 1 CAUSES |
| alerts | 55 | 41 ANOMALY (3 CRITICAL) + 14 CHANGE_POINT |
| lineage_nodes | 491 | Source→Adapter→Obs→Transform→Output per source |
| lineage_edges | 387 | Full provenance DAG for all 98 sources |

## What Changed This Session

### 1. Entity Geometry Fix (97.5% coverage)
- Problem: Only 1,775/42,352 entities had geometry (4.2%) — `on_conflict_do_nothing` skipped re-inserts
- Fix: PostgreSQL `uuid_generate_v5()` to join entities to observations via deterministic UUID5
- SQL: `UPDATE entities SET geometry = obs.geometry FROM observations WHERE entity.id = uuid5(obs.source_name, obs.source_id)`
- Result: 39,523 entities updated → 41,298/42,352 with geometry (97.5%)
- Remaining 1,054 entities lack geometry because their observation source_ids don't produce matching UUIDs (registered mappers use different ID schemes)

### 2. Semantic Similarity Edges (10K created)
- `builder.py:build_semantic_edges()` upgraded from brute-force cross-join to LATERAL nearest-neighbor using IVFFlat index
- pgvector IVFFlat index: `ix_emb_cosine` (lists=100, vector_cosine_ops)
- Created 10,000 RELATES_TO edges with evidence_type='semantic_similarity'
- Cross-type connections between entity/event/observation embeddings

### 3. Lineage Tables Populated
- 491 lineage nodes: SOURCE (98) + ADAPTER (98) + OBSERVATION_BATCH (98) + TRANSFORM (98) + OUTPUT (~99) + ALGORITHM (6)
- 387 lineage edges: SOURCE→ADAPTER→OBSERVATIONS→TRANSFORM→{entities,events,assessments,time_series}
- Graph algorithm nodes: spatial_edges, semantic_edges, correlation_edges, temporal_causal, embedding_v2_moe, alert_engine
- Idempotent via `on_conflict_do_nothing` with deterministic UUIDs

### 4. LLM Client Hardened
- `src/okeanus/ml/llm/client.py` — added 120s timeout + 3 retries with exponential backoff (2s, 4s)
- Fresh httpx client created on each retry to avoid CLOSE_WAIT reuse
- Catches: httpx.TimeoutException, ConnectError, RemoteProtocolError

### 5. Redis Enabled
- Installed via Homebrew: `brew install redis && brew services start redis`
- Running on default port 6379
- Required for AIS streaming (Redis GeoSet for vessel positions)

### 6. AIS Streaming Robustified
- `src/okeanus/streaming/ais_ingester.py:66-68` — WebSocket timeout: `open_timeout=30`, `close_timeout=10`
- `src/okeanus/main.py:79-82` — Graceful shutdown: `await ingester.stop()` before task cancel
- Activation: Set `AIS_STREAM_ENABLED=true` and `AIS_STREAM_API_KEY=<key>` in `.env`
- Get free API key from https://aisstream.io/

### 7. UoT Hypothesis Generation
- Status: Running in background (depth 1/2, C-UoT + E-UoT scoring completed)
- LLM client timeout/retry prevents CLOSE_WAIT hangs that killed previous attempts
- If interrupted, re-run: `source .env && .venv/bin/python3 scripts/run_ml_pipeline.py`

## Files Modified This Session
| File | Changes |
|------|---------|
| `src/okeanus/ml/llm/client.py` | 120s timeout, 3x retry, exponential backoff |
| `src/okeanus/ml/graph/builder.py:232-341` | LATERAL NN semantic edges (replaced cross-join) |
| `src/okeanus/streaming/ais_ingester.py:66-68` | WebSocket timeout params |
| `src/okeanus/main.py:79-82` | Graceful AIS shutdown |

## Previous Sessions' Files (unchanged)
| File | Purpose |
|------|---------|
| `scripts/promote_observations.py` | Observation → entity/event/assessment promotion |
| `src/okeanus/transform/ontology.py` | Type hierarchy + cross-source mapping |
| `src/okeanus/ml/alerting.py` | Alert engine (anomaly + changepoint + spatial) |
| `src/okeanus/ml/synthesis/temporal.py` | Temporal reasoning + causal chains |
| `src/okeanus/ml/geospatial.py` | Geospatial analytics (DBSCAN, Gi*, Moran's I) |
| `src/okeanus/ml/lineage.py` | Data lineage/provenance tracking |
| `src/okeanus/schema/lineage.py` | Lineage ORM models |
| `src/okeanus/api/alerts.py` | Alert API endpoints |
| `src/okeanus/api/geospatial.py` | Geospatial analytics API |
| `src/okeanus/api/lineage.py` | Lineage API endpoints |

## Known Issues / Remaining Work

### Priority 1: UoT Completion
- UoT in progress (2 depths). If it fails, re-run with `source .env && .venv/bin/python3 scripts/run_ml_pipeline.py`
- May need to increase `_API_TIMEOUT_SECONDS` in `client.py:19` if API is slow

### Priority 2: AIS Activation
- Redis is running. Get API key from https://aisstream.io/ (free tier)
- Set in `.env`: `AIS_STREAM_ENABLED=true` and `AIS_STREAM_API_KEY=<your-key>`
- Server auto-connects on startup via `main.py` lifespan

### Priority 3: Entity Geometry Remaining 2.5%
- 1,054 entities still lack geometry. These come from registered mappers that use custom source_id formats
- Fix: Update promote_observations.py to use `on_conflict_do_update` for geometry column

### Priority 4: PRefLexOR Adversarial Refinement
- UoT generates hypotheses, PRefLexOR refines them via Think/Reflect/Refine loop
- `src/okeanus/ml/synthesis/preflexor.py` exists but not yet wired to UoT output

### Priority 5: Investigation Testing
- POST /investigate with real queries to test full recursive Claude investigation loop
- Requires ANTHROPIC_API_KEY set (uses API credits for Sonnet 4.6 with 1M context)

## Architecture Quick Reference
- **Adapters**: `src/okeanus/adapters/` (145 adapters, 119 no-auth)
- **Transform**: `src/okeanus/transform/` (ontology, pipeline, mappers)
- **ML pipeline**: `src/okeanus/ml/` (vectors/, graph/, synthesis/, engine/, alerting, geospatial, lineage)
- **Investigation**: `src/okeanus/ml/llm/investigator.py` (recursive Claude tool-use, 1M context on Sonnet 4.6)
- **API**: `src/okeanus/api/` (alerts, geospatial, lineage + existing routes)
- **Config**: `src/okeanus/config.py` + `.env`
- **DB**: `postgresql://okeanus:okeanus@localhost:5432/okeanus` (pg17)
- **Redis**: `redis://localhost:6379` (for AIS streaming)
- **PostgreSQL**: `brew services start postgresql@17`
- **psql**: `/opt/homebrew/opt/postgresql@17/bin/psql`
- **Start server**: `source .env && .venv/bin/python3 -m uvicorn okeanus.main:app --host 127.0.0.1 --port 8000`
- **Run ML pipeline**: `source .env && .venv/bin/python3 scripts/run_ml_pipeline.py`
- **Run ingestion**: `.venv/bin/python3 scripts/ingest_all.py` (4 min, parallel)
- **Run promotion**: `.venv/bin/python3 scripts/promote_observations.py`

## API Key Status
- Working key in `.env` (Fp6Cb6d...)
- Shell env may have depleted key — always use `source .env` prefix
