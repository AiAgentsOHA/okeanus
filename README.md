# Okeanus -- Unified Ocean Intelligence Platform

Fuses underwater acoustics, satellite imagery, and AIS vessel tracking into a single queryable ocean data layer. Built on EDITO (EU Digital Twin Ocean).

## Architecture

```
+---------------------+
|     API Layer       |   FastAPI endpoints, WebSocket streams
|   (src/okeanus/api) |
+----------+----------+
           |
+----------v----------+
|   Domain / Schema   |   Pydantic models, GeoJSON types
| (src/okeanus/schema)|
+----------+----------+
           |
+----------v----------+
|    Data Layer        |   PostGIS (spatial), DuckDB (analytics)
|  (src/okeanus/db)   |
+---------------------+
```

## Quick Start

```bash
# Clone and start services
git clone <repo-url> && cd okeanus
cp .env.example .env
docker compose up -d

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

## Development

```bash
# Install in dev mode
pip install -e ".[dev]"

# Run checks
ruff check src/ tests/
pytest
```

## Tech Stack

- **Python 3.12** -- runtime
- **FastAPI** -- async HTTP/WebSocket API
- **PostGIS** -- spatial data storage and queries
- **DuckDB** -- columnar analytics engine
- **SQLAlchemy 2.0** -- async ORM with GeoAlchemy2
- **Alembic** -- database migrations
