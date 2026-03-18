"""BGE-small-en-v1.5 embedding generator with lazy model loading."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Lazy-load the sentence-transformers model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        from okeanus.config import settings
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
    return _model


class OceanEmbedder:
    """Generate embeddings for ocean data text using BGE-small."""

    def embed_texts(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        """Embed a list of texts, returns (N, 384) float32 array."""
        model = _get_model()
        return model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single text, returns (384,) float32 array."""
        return self.embed_texts([text])[0]

    def text_for_entity(self, entity: dict[str, Any]) -> str:
        """Build embeddable text from an entity dict."""
        parts = []
        if entity.get("name"):
            parts.append(entity["name"])
        if entity.get("entity_type"):
            parts.append(f"[{entity['entity_type']}]")
        if entity.get("sector"):
            parts.append(f"sector: {entity['sector']}")
        if entity.get("country"):
            parts.append(f"country: {entity['country']}")
        payload = entity.get("payload") or {}
        if isinstance(payload, dict):
            desc = payload.get("description", "")
            if desc:
                parts.append(str(desc)[:500])
        return " | ".join(parts) if parts else str(entity.get("source_id", ""))

    def text_for_observation(self, obs: dict[str, Any]) -> str:
        """Build embeddable text from an observation dict."""
        parts = []
        if obs.get("source_name"):
            parts.append(obs["source_name"])
        if obs.get("parameter"):
            parts.append(obs["parameter"])
        payload = obs.get("payload") or {}
        if isinstance(payload, dict):
            for k in ("parameter", "value", "unit", "species_name", "description"):
                if payload.get(k):
                    parts.append(f"{k}: {payload[k]}")
        return " | ".join(parts) if parts else "observation"

    def text_for_event(self, event: dict[str, Any]) -> str:
        """Build embeddable text from an event dict."""
        parts = []
        if event.get("event_type"):
            parts.append(f"[{event['event_type']}]")
        if event.get("name"):
            parts.append(event["name"])
        if event.get("description"):
            parts.append(str(event["description"])[:500])
        return " | ".join(parts) if parts else "event"
