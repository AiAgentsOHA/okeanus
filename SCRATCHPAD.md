# Session 42 — Data Pipeline + Decision Intelligence

## Current State
- Backend: running on :8000, frontend on :3000
- Last commit: `cae6b2b` on main (uncommitted changes below)
- Adapter batch round 2 running (b5bfe6e) — Atlantic bbox, 38 adapters
- Round 1 results: 2 succeeded (fathomnet 500, gbif 293), 6 empty, 38 errors (mostly API/timeout)

## Changes Made This Session (UNCOMMITTED)

### Frontend fixes
- `dashboard/src/lib/api.ts` — fixed investigate path (`/ml/investigate`), density path (`/entities/density`)
- `dashboard/src/app/page.tsx` — fixed density fetch path

### Backend: new endpoints
- `src/okeanus/api/analytics.py` — added `/analytics/hotspots` (reuses density with min_count filter)
- `src/okeanus/main.py` — added `/search` POST (pg_trgm similarity on entities)

### Pipeline wiring
- `src/okeanus/api/ingest.py` — added lineage tracking after observation ingest
- `src/okeanus/transform/store.py` — added lineage tracking for transformed records
- `src/okeanus/ml/engine/routes.py` — added `/ml/intelligence/pipeline/run` (DuckDB sync → embed → backfill → NetworkX rebuild)

### Temporary
- `run_missing_adapters.py` — batch ingest script

## Pipeline Architecture (verified)
- **Automated**: ingest → transform (economic) → basic graph edges → lineage (NEW)
- **Manual**: embeddings, full graph backfill, NetworkX rebuild, insight generation
- **NEW `/pipeline/run`**: chains all manual steps in one POST call
- **Still disconnected**: reasoning_traces (UoT doesn't log steps), decision tree frontend

## Next Session TODO
1. Check round 2 adapter results, fix remaining failures
2. Run full pipeline: `POST /ml/intelligence/pipeline/run`
3. Wire reasoning_traces into insight_generator.py
4. Build decision tree frontend component (lineage visualization)
5. Add `/lineage/{entity_id}/tree` endpoint for decision provenance
