"""Batch and incremental embedding indexer."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.config import settings
from okeanus.ml.vectors.embedder import OceanEmbedder

logger = logging.getLogger(__name__)


class EmbeddingIndexer:
    """Build and maintain the embeddings table."""

    def __init__(self) -> None:
        self._embedder = OceanEmbedder()

    async def build_full_index(
        self,
        session: AsyncSession,
        batch_size: int = 200,
    ) -> dict[str, int]:
        """Build embeddings for all entities, events, and observations."""
        counts: dict[str, int] = {}

        # Entities
        from okeanus.schema.economy import Entity
        entity_rows = (await session.execute(
            select(Entity.id, Entity.name, Entity.entity_type, Entity.sector,
                   Entity.country, Entity.payload, Entity.source_id)
        )).fetchall()

        if entity_rows:
            texts = []
            meta = []
            for row in entity_rows:
                d = {
                    "name": row.name, "entity_type": row.entity_type,
                    "sector": row.sector, "country": row.country,
                    "payload": row.payload, "source_id": row.source_id,
                }
                texts.append(self._embedder.text_for_entity(d))
                meta.append({"id": row.id, "source_type": "entity", "table": "entities"})

            embeddings = self._embedder.embed_texts(texts, batch_size=batch_size)
            await self._upsert_embeddings(session, texts, embeddings, meta)
            counts["entities"] = len(entity_rows)

        # Events
        from okeanus.schema.economy import Event
        event_rows = (await session.execute(
            select(Event.id, Event.event_type, Event.name, Event.description)
        )).fetchall()

        if event_rows:
            texts = []
            meta = []
            for row in event_rows:
                d = {"event_type": row.event_type, "name": row.name,
                     "description": row.description}
                texts.append(self._embedder.text_for_event(d))
                meta.append({"id": row.id, "source_type": "event", "table": "events"})

            embeddings = self._embedder.embed_texts(texts, batch_size=batch_size)
            await self._upsert_embeddings(session, texts, embeddings, meta)
            counts["events"] = len(event_rows)

        # Observations — paginated to handle 65K+ rows
        from okeanus.schema.base import Observation
        total_obs = (await session.execute(
            select(func.count(Observation.id))
        )).scalar() or 0

        if total_obs > 0:
            logger.info("Embedding %d observations in pages of 1000...", total_obs)
            obs_embedded = 0
            page_size = 1000
            offset = 0

            while offset < total_obs:
                obs_rows = (await session.execute(
                    select(
                        Observation.id, Observation.obs_type,
                        Observation.source_name, Observation.payload,
                    )
                    .order_by(Observation.id)
                    .offset(offset)
                    .limit(page_size)
                )).fetchall()

                if not obs_rows:
                    break

                texts = []
                meta = []
                for row in obs_rows:
                    d = {
                        "source_name": row.source_name,
                        "parameter": row.obs_type,
                        "payload": row.payload,
                    }
                    texts.append(self._embedder.text_for_observation(d))
                    meta.append({
                        "id": row.id,
                        "source_type": "observation",
                        "table": "observations",
                    })

                embeddings = self._embedder.embed_texts(texts, batch_size=batch_size)
                await self._upsert_embeddings(session, texts, embeddings, meta)
                await session.flush()

                obs_embedded += len(obs_rows)
                offset += page_size
                logger.info(
                    "Observations: %d / %d embedded (%.0f%%)",
                    obs_embedded, total_obs, obs_embedded / total_obs * 100,
                )

            counts["observations"] = obs_embedded

        return counts

    async def index_new_items(
        self,
        session: AsyncSession,
        items: list[dict[str, Any]],
        source_type: str,
        source_table: str,
    ) -> int:
        """Index a batch of new items (called from store hook)."""
        if not items:
            return 0

        text_fn = {
            "entity": self._embedder.text_for_entity,
            "event": self._embedder.text_for_event,
            "observation": self._embedder.text_for_observation,
        }.get(source_type, self._embedder.text_for_observation)

        texts = [text_fn(item) for item in items]
        meta = [
            {"id": item.get("id"), "source_type": source_type, "table": source_table}
            for item in items
        ]
        embeddings = self._embedder.embed_texts(texts)
        await self._upsert_embeddings(session, texts, embeddings, meta)
        return len(items)

    async def _upsert_embeddings(
        self,
        session: AsyncSession,
        texts: list[str],
        embeddings,
        meta: list[dict],
    ) -> None:
        """Insert embedding rows, skip duplicates by source_id."""
        import uuid as uuid_mod
        for i, (txt, emb, m) in enumerate(zip(texts, embeddings, meta)):
            vec_str = "[" + ",".join(str(float(v)) for v in emb) + "]"
            await session.execute(
                text("""
                    INSERT INTO embeddings (id, source_id, source_type, source_table,
                                           text_content, embedding, model_name)
                    VALUES (:id, :source_id, :source_type, :source_table,
                            :text_content, CAST(:embedding AS vector), :model_name)
                    ON CONFLICT ON CONSTRAINT uq_emb_source DO UPDATE
                    SET text_content = EXCLUDED.text_content,
                        embedding = EXCLUDED.embedding,
                        created_at = now()
                """),
                {
                    "id": str(uuid_mod.uuid4()),
                    "source_id": str(m["id"]),
                    "source_type": m["source_type"],
                    "source_table": m["table"],
                    "text_content": txt[:2000],
                    "embedding": vec_str,
                    "model_name": settings.embedding_model,
                },
            )

    async def embedding_stats(self, session: AsyncSession) -> dict[str, Any]:
        """Return summary stats of the embeddings table."""
        result = await session.execute(text(
            "SELECT source_type, count(*) FROM embeddings GROUP BY source_type"
        ))
        by_type = {row[0]: row[1] for row in result.fetchall()}
        total = sum(by_type.values())
        return {"total": total, "by_source_type": by_type}
