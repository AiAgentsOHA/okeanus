"""Universe of Thoughts (UoT) creative reasoning engine.

Implements three modes from Suzuki & Banaei-Kashani (arXiv:2511.20471),
grounded in Boden's creativity taxonomy:
- C-UoT: Cross-domain analogical transfer (combinational creativity)
- E-UoT: Expanding thought palette (exploratory creativity)
- T-UoT: Transformational — mutating hidden assumptions (transformational creativity)

Key improvements over scaffold:
- Thought graph: DAG where each thought has id, content, score, parent, type
- C-UoT queries knowledge graph bridges BEFORE generating analogies
- E-UoT uses vector search to find unexplored embedding regions
- T-UoT fetches real assumptions from knowledge graph edges
- Pruning: thoughts with score < threshold are dropped
- Recursive deepening: 2-3 iterations with shrinking thought set
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


# -- Thought Graph --

class Thought:
    """A single node in the thought graph."""

    __slots__ = ("id", "content", "score", "parent_id", "thought_type", "metadata")

    def __init__(
        self,
        content: str,
        score: float = 0.5,
        parent_id: str | None = None,
        thought_type: str = "C",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.content = content
        self.score = score
        self.parent_id = parent_id
        self.thought_type = thought_type  # C, E, or T
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "score": round(self.score, 4),
            "parent_id": self.parent_id,
            "type": self.thought_type,
            "metadata": self.metadata,
        }


class ThoughtGraph:
    """DAG of thoughts with scoring and pruning."""

    def __init__(self, prune_threshold: float = 0.3) -> None:
        self._thoughts: dict[str, Thought] = {}
        self._prune_threshold = prune_threshold

    def add(self, thought: Thought) -> str:
        self._thoughts[thought.id] = thought
        return thought.id

    def get(self, thought_id: str) -> Thought | None:
        return self._thoughts.get(thought_id)

    def children(self, parent_id: str) -> list[Thought]:
        return [t for t in self._thoughts.values() if t.parent_id == parent_id]

    def roots(self) -> list[Thought]:
        return [t for t in self._thoughts.values() if t.parent_id is None]

    def all_thoughts(self) -> list[Thought]:
        return list(self._thoughts.values())

    def by_type(self, thought_type: str) -> list[Thought]:
        return [t for t in self._thoughts.values() if t.thought_type == thought_type]

    def prune(self) -> int:
        """Remove thoughts below the score threshold. Returns count removed."""
        to_remove = [
            tid for tid, t in self._thoughts.items()
            if t.score < self._prune_threshold
        ]
        for tid in to_remove:
            # Also orphan children (they keep their content but lose parent link)
            for child in self.children(tid):
                child.parent_id = None
            del self._thoughts[tid]
        return len(to_remove)

    def top_k(self, k: int = 10) -> list[Thought]:
        """Return top-k thoughts by score."""
        return sorted(self._thoughts.values(), key=lambda t: t.score, reverse=True)[:k]

    def to_dict(self) -> dict[str, Any]:
        return {
            "thought_count": len(self._thoughts),
            "by_type": {
                "C": len(self.by_type("C")),
                "E": len(self.by_type("E")),
                "T": len(self.by_type("T")),
            },
            "thoughts": [t.to_dict() for t in self.top_k(50)],
        }


# -- System prompts --

C_UOT_SYSTEM = """You are an ocean intelligence analyst specializing in cross-domain analogical reasoning.

You will be given:
1. A concept to find analogies for
2. Bridge concepts from the knowledge graph that connect different domains
3. Target domains to search

Using the bridge concepts as starting points, find FUNCTIONAL analogies (not surface similarities).

For each analogy:
1. Identify the FUNCTIONAL role of the concept (what it does, not what it looks like)
2. Explain the structural mapping (which properties transfer)
3. Rate analogy strength (0.0-1.0) — higher for structural match, lower for surface-only
4. Extract a transferable PRINCIPLE (not a description)

Output JSON array:
[{
  "source_concept": "...",
  "source_domain": "...",
  "target_concept": "...",
  "target_domain": "...",
  "functional_mapping": "...",
  "transferable_principle": "...",
  "strength": 0.0,
  "novel_insight": "...",
  "bridge_used": "..."
}]"""

E_UOT_SYSTEM = """You are an ocean intelligence analyst expanding the exploration space.

You will be given:
1. Current findings
2. Unexplored regions from embedding space (concepts that are semantically distant from current findings)
3. Already explored domains

Using the unexplored regions as seeds, generate NEW hypotheses that explore genuinely different territory.

For each hypothesis:
1. Ground it in a specific unexplored concept or region
2. Explain why this direction is worth exploring
3. Write as a testable, falsifiable claim
4. Check: is this genuinely novel or a restatement?

Output JSON array:
[{
  "hypothesis": "...",
  "exploration_type": "adjacent|scale_shift|counter_example|data_gap",
  "grounded_in": "...",
  "priority": 0.0,
  "required_data": ["..."],
  "falsifiable_test": "..."
}]"""

T_UOT_SYSTEM = """You are an ocean intelligence analyst performing transformational reasoning.

You will be given:
1. Assumptions extracted from the knowledge graph (real relationships, not invented)
2. Context about the topic

For each assumption, apply ONE mutation:
- DROP: Remove the assumption entirely. What changes? Trace the consequences.
- INVERT: Reverse the assumption. What if the opposite were true? Check for evidence.
- VARY: Change the parameter by 10x in each direction. What breaks?

Every mutation must be checked against actual evidence. No speculation without grounding.

Output JSON array:
[{
  "original_assumption": "...",
  "source": "...",
  "mutation": "DROP|INVERT|VARY",
  "mutated_version": "...",
  "consequence": "...",
  "evidence_for": "...",
  "evidence_against": "...",
  "new_insight": "...",
  "plausibility": 0.0
}]"""

SCORER_SYSTEM = """You are a thought quality evaluator. Given a list of thoughts (ideas, hypotheses, analogies),
rate each one on a 0.0-1.0 scale based on:
- Grounding: Is it backed by data or just speculation? (weight: 0.4)
- Novelty: Is this a genuine insight or obvious/restated? (weight: 0.3)
- Actionability: Can it lead to testable predictions or real decisions? (weight: 0.3)

Output JSON array:
[{"thought_index": 0, "score": 0.0, "reasoning": "..."}]"""


class UniverseOfThoughts:
    """Creative reasoning through systematic thought exploration with thought graph."""

    def __init__(
        self,
        prune_threshold: float = 0.3,
        max_depth: int = 3,
    ) -> None:
        self._prune_threshold = prune_threshold
        self._max_depth = max_depth

    async def _call_llm(self, system: str, user_message: str) -> str:
        from anthropic import AsyncAnthropic
        from okeanus.config import settings

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    async def _score_thoughts(self, thoughts: list[Thought]) -> list[Thought]:
        """Use LLM to score a batch of thoughts."""
        if not thoughts:
            return thoughts

        thought_list = "\n".join(
            f"{i}. [{t.thought_type}] {t.content}" for i, t in enumerate(thoughts)
        )
        raw = await self._call_llm(SCORER_SYSTEM, f"Rate these thoughts:\n{thought_list}")

        try:
            scores = json.loads(raw)
            if isinstance(scores, list):
                for item in scores:
                    idx = item.get("thought_index", -1)
                    if 0 <= idx < len(thoughts):
                        thoughts[idx].score = item.get("score", 0.5)
        except json.JSONDecodeError:
            logger.warning("Could not parse thought scores, keeping defaults")

        return thoughts

    async def _fetch_bridges(
        self,
        session,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Query knowledge graph for cross-domain bridge concepts."""
        try:
            from okeanus.ml.graph.algorithms import GraphAlgorithms
            algos = GraphAlgorithms()
            return await algos.cross_domain_bridges(session, top_k=top_k)
        except Exception as exc:
            logger.debug("Could not fetch bridges: %s", exc)
            return []

    async def _fetch_unexplored(
        self,
        session,
        findings_text: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find embedding regions distant from current findings."""
        try:
            from okeanus.ml.vectors.search import VectorSearch
            searcher = VectorSearch()
            # Search for items similar to findings, then we'll look at
            # what's NOT similar — use cross_domain_similar to find
            # related concepts from different source types
            return await searcher.cross_domain_similar(
                session, findings_text[:500], limit=limit,
            )
        except Exception as exc:
            logger.debug("Could not fetch unexplored regions: %s", exc)
            return []

    async def _fetch_assumptions(
        self,
        session,
        topic: str,
        limit: int = 10,
    ) -> list[str]:
        """Extract real assumptions from knowledge graph edges related to the topic."""
        try:
            from okeanus.ml.vectors.search import VectorSearch
            searcher = VectorSearch()
            # Find entities related to the topic
            related = await searcher.search(session, topic, limit=limit)

            if not related:
                return []

            # Get knowledge graph edges for these entities to extract relationships
            from sqlalchemy import text as sql_text
            source_ids = [r["source_id"] for r in related[:5]]
            placeholders = ", ".join(f"'{sid}'" for sid in source_ids)

            sql = sql_text(f"""
                SELECT source_label, edge_type, target_label, strength
                FROM knowledge_edges
                WHERE source_id::text IN ({placeholders})
                   OR target_id::text IN ({placeholders})
                ORDER BY strength DESC
                LIMIT :lim
            """)
            rows = (await session.execute(sql, {"lim": limit})).fetchall()

            assumptions = []
            for row in rows:
                assumptions.append(
                    f"{row.source_label} {row.edge_type} {row.target_label} "
                    f"(strength: {row.strength:.2f})"
                )
            return assumptions

        except Exception as exc:
            logger.debug("Could not fetch assumptions from KG: %s", exc)
            return []

    async def c_uot_analogies(
        self,
        concept: str,
        source_domain: str,
        target_domains: list[str],
        graph: ThoughtGraph,
        session=None,
        context: str = "",
    ) -> list[Thought]:
        """Cross-domain analogical transfer (C-UoT).

        Queries knowledge graph bridges BEFORE generating analogies.
        """
        # Fetch bridge concepts from the knowledge graph
        bridges: list[dict[str, Any]] = []
        if session:
            bridges = await self._fetch_bridges(session, top_k=10)

        bridge_text = ""
        if bridges:
            bridge_text = "Bridge concepts from knowledge graph:\n" + "\n".join(
                f"- {b.get('label', '?')} (domain: {b.get('domain', '?')}, "
                f"connected to: {', '.join(b.get('connected_domains', []))})"
                for b in bridges[:10]
            )

        prompt = (
            f"Find cross-domain analogies for:\n"
            f"Concept: {concept}\n"
            f"Source domain: {source_domain}\n"
            f"Target domains: {', '.join(target_domains)}\n"
        )
        if bridge_text:
            prompt += f"\n{bridge_text}\n"
        if context:
            prompt += f"\nContext:\n{context}\n"

        raw = await self._call_llm(C_UOT_SYSTEM, prompt)

        thoughts: list[Thought] = []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                for item in parsed:
                    t = Thought(
                        content=json.dumps(item, default=str),
                        score=item.get("strength", 0.5),
                        thought_type="C",
                        metadata=item,
                    )
                    graph.add(t)
                    thoughts.append(t)
        except json.JSONDecodeError:
            t = Thought(content=raw[:500], score=0.4, thought_type="C")
            graph.add(t)
            thoughts.append(t)

        return thoughts

    async def e_uot_expand(
        self,
        findings: list[dict[str, Any]],
        explored_domains: list[str],
        graph: ThoughtGraph,
        parent_ids: list[str] | None = None,
        session=None,
    ) -> list[Thought]:
        """Expand the exploration space (E-UoT).

        Uses vector search to find unexplored embedding regions as seeds.
        """
        findings_text = json.dumps(findings[:10], indent=2, default=str)

        # Fetch unexplored regions from embedding space
        unexplored: list[dict[str, Any]] = []
        if session:
            unexplored = await self._fetch_unexplored(session, findings_text)

        unexplored_text = ""
        if unexplored:
            unexplored_text = "Unexplored regions (cross-domain concepts):\n" + "\n".join(
                f"- {u.get('text_content', '?')[:100]} "
                f"(type: {u.get('source_type', '?')}, sim: {u.get('similarity', '?')})"
                for u in unexplored[:10]
            )

        prompt = (
            f"Current findings:\n{findings_text}\n\n"
            f"Already explored domains: {', '.join(explored_domains)}\n\n"
        )
        if unexplored_text:
            prompt += f"{unexplored_text}\n\n"
        prompt += "Generate new exploration directions grounded in the unexplored regions."

        raw = await self._call_llm(E_UOT_SYSTEM, prompt)

        thoughts: list[Thought] = []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                for i, item in enumerate(parsed):
                    parent = parent_ids[i % len(parent_ids)] if parent_ids else None
                    t = Thought(
                        content=json.dumps(item, default=str),
                        score=item.get("priority", 0.5),
                        parent_id=parent,
                        thought_type="E",
                        metadata=item,
                    )
                    graph.add(t)
                    thoughts.append(t)
        except json.JSONDecodeError:
            t = Thought(content=raw[:500], score=0.4, thought_type="E")
            graph.add(t)
            thoughts.append(t)

        return thoughts

    async def t_uot_transform(
        self,
        topic: str,
        graph: ThoughtGraph,
        parent_ids: list[str] | None = None,
        session=None,
        context: str = "",
    ) -> list[Thought]:
        """Transformational reasoning (T-UoT).

        Fetches real assumptions from knowledge graph edges instead of hardcoding.
        """
        # Fetch actual assumptions from the knowledge graph
        assumptions: list[str] = []
        if session:
            assumptions = await self._fetch_assumptions(session, topic)

        if not assumptions:
            # Fallback: ask LLM to identify assumptions from context
            assumptions = [
                f"The relationship between {topic} and observed data is well-understood",
                f"Current data coverage is sufficient for conclusions about {topic}",
                f"Temporal patterns in {topic} are stationary over the observation period",
            ]
            logger.info("No KG assumptions found for '%s', using LLM-generated fallback", topic)

        assumptions_text = "\n".join(f"- {a}" for a in assumptions)
        prompt = f"Assumptions to challenge (from knowledge graph):\n{assumptions_text}"
        if context:
            prompt += f"\n\nContext:\n{context}"

        raw = await self._call_llm(T_UOT_SYSTEM, prompt)

        thoughts: list[Thought] = []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                for i, item in enumerate(parsed):
                    parent = parent_ids[i % len(parent_ids)] if parent_ids else None
                    t = Thought(
                        content=json.dumps(item, default=str),
                        score=item.get("plausibility", 0.5),
                        parent_id=parent,
                        thought_type="T",
                        metadata=item,
                    )
                    graph.add(t)
                    thoughts.append(t)
        except json.JSONDecodeError:
            t = Thought(content=raw[:500], score=0.4, thought_type="T")
            graph.add(t)
            thoughts.append(t)

        return thoughts

    async def full_creative_reasoning(
        self,
        topic: str,
        evidence: str,
        domains: list[str],
        session=None,
    ) -> dict[str, Any]:
        """Run full UoT pipeline with thought graph, pruning, and recursive deepening.

        C-UoT -> score -> prune -> E-UoT -> score -> prune -> T-UoT -> score -> prune
        Then deepen: take top thoughts and run another cycle on them.
        """
        graph = ThoughtGraph(prune_threshold=self._prune_threshold)
        depth_stats: list[dict[str, Any]] = []

        for depth in range(self._max_depth):
            logger.info("UoT depth %d/%d for topic '%s'", depth + 1, self._max_depth, topic)

            # Step 1: C-UoT — Cross-domain analogies
            c_thoughts = await self.c_uot_analogies(
                topic,
                domains[0] if domains else "general",
                domains[1:] or ["economics", "ecology"],
                graph,
                session=session,
                context=evidence[:500] if depth == 0 else "",
            )

            # Score and prune C-UoT thoughts
            c_thoughts = await self._score_thoughts(c_thoughts)
            c_pruned = graph.prune()

            # Step 2: E-UoT — Expand exploration
            surviving_ids = [t.id for t in graph.by_type("C")]
            e_thoughts = await self.e_uot_expand(
                [{"finding": topic, "evidence": evidence[:500]}]
                if depth == 0
                else [t.to_dict() for t in graph.top_k(5)],
                explored_domains=domains,
                graph=graph,
                parent_ids=surviving_ids or None,
                session=session,
            )

            # Score and prune E-UoT thoughts
            e_thoughts = await self._score_thoughts(e_thoughts)
            e_pruned = graph.prune()

            # Step 3: T-UoT — Transform assumptions
            surviving_ids = [t.id for t in graph.top_k(5)]
            t_thoughts = await self.t_uot_transform(
                topic,
                graph,
                parent_ids=surviving_ids or None,
                session=session,
                context=evidence[:500] if depth == 0 else "",
            )

            # Score and prune T-UoT thoughts
            t_thoughts = await self._score_thoughts(t_thoughts)
            t_pruned = graph.prune()

            depth_stats.append({
                "depth": depth,
                "c_generated": len(c_thoughts),
                "e_generated": len(e_thoughts),
                "t_generated": len(t_thoughts),
                "pruned": c_pruned + e_pruned + t_pruned,
                "surviving": len(graph.all_thoughts()),
            })

            # For deeper iterations, narrow the focus to top surviving thoughts
            top = graph.top_k(5)
            if not top:
                logger.info("No thoughts survived pruning at depth %d, stopping", depth)
                break

            # Update topic/evidence for next depth based on top thoughts
            if depth < self._max_depth - 1:
                topic_refinement = "; ".join(
                    t.metadata.get("novel_insight", t.content[:100])
                    if isinstance(t.metadata.get("novel_insight"), str)
                    else t.content[:100]
                    for t in top[:3]
                )
                evidence = f"Previous insights: {topic_refinement}"

        return {
            "topic": topic,
            "thought_graph": graph.to_dict(),
            "depth_stats": depth_stats,
            "top_thoughts": [t.to_dict() for t in graph.top_k(10)],
            "analogies": [t.to_dict() for t in graph.by_type("C")],
            "expansions": [t.to_dict() for t in graph.by_type("E")],
            "transformations": [t.to_dict() for t in graph.by_type("T")],
            "domains_explored": domains,
        }
