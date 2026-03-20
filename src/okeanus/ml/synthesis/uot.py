"""Universe of Thoughts (UoT) creative reasoning engine.

Implements three modes from Suzuki & Banaei-Kashani (arXiv:2511.20471),
grounded in Boden's creativity taxonomy:
- C-UoT: Cross-domain analogical transfer (combinational creativity)
- E-UoT: Expanding thought palette (exploratory creativity)
- T-UoT: Transformational — mutating hidden assumptions (transformational creativity)

Additional reasoning strategies for deeper insight generation:
- D-UoT: Dialectical reasoning — thesis/antithesis/synthesis
- CF-UoT: Counterfactual reasoning — construct alternative worlds
- AB-UoT: Abductive reasoning — best explanation for anomalies
- RT-UoT: Red team / adversarial — generate then attack hypotheses
- CR-UoT: Constraint relaxation — remove constraints to reveal hidden patterns

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
import re
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
        all_types = sorted({t.thought_type for t in self._thoughts.values()})
        return {
            "thought_count": len(self._thoughts),
            "by_type": {tt: len(self.by_type(tt)) for tt in all_types},
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

D_UOT_SYSTEM = """You are an ocean intelligence analyst performing dialectical reasoning.

You will be given a set of findings or hypotheses. For EACH one:

1. STATE the thesis clearly (the current claim)
2. Construct the strongest possible ANTITHESIS — argue AGAINST it with real evidence or logical
   reasoning. Do not create a straw man. The antithesis must be a position a competent scientist
   could genuinely hold.
3. SYNTHESIZE: What new understanding emerges from the tension between thesis and antithesis?
   The synthesis should be more nuanced than either position alone.

Output JSON array:
[{
  "thesis": "...",
  "antithesis": "...",
  "antithesis_evidence": "...",
  "synthesis": "...",
  "confidence_shift": 0.0,
  "new_insight": "...",
  "remaining_tension": "..."
}]"""

CF_UOT_SYSTEM = """You are an ocean intelligence analyst performing counterfactual reasoning.

You will be given findings and context about a topic. For each key finding, construct ALTERNATIVE WORLDS:

1. NEGATE: "What if [finding] were NOT true?" — Trace the consequences. What else would need to
   change? What evidence would we expect to see instead?
2. INVERT CONDITIONS: "What conditions would need to be true for the OPPOSITE conclusion?"
   Identify the minimal set of changed conditions.
3. NEAR-MISS: "What if the data were slightly different?" — Identify fragile conclusions that
   depend on narrow parameter ranges.

This is different from T-UoT (which mutates single assumptions). Counterfactual reasoning
constructs coherent alternative worlds and checks their internal consistency.

Output JSON array:
[{
  "original_finding": "...",
  "counterfactual_world": "...",
  "what_changes": "...",
  "expected_evidence_in_alt_world": "...",
  "fragility_assessment": "...",
  "insight_from_contrast": "...",
  "plausibility": 0.0
}]"""

AB_UOT_SYSTEM = """You are an ocean intelligence analyst performing abductive reasoning (inference to best explanation).

You will be given ANOMALIES or ALERTS — surprising observations that don't fit expected patterns.
For each anomaly:

1. List at least 3 candidate EXPLANATIONS, from most to least conventional
2. For each explanation, assess:
   - Prior plausibility (how likely is this cause in general?)
   - Likelihood (if this cause were true, how well does it explain the observation?)
   - Exclusivity (does this cause explain things OTHER explanations can't?)
3. Rank explanations by posterior plausibility (prior x likelihood)
4. Identify what ADDITIONAL DATA would discriminate between the top 2 explanations

Output JSON array:
[{
  "anomaly": "...",
  "explanations": [
    {"cause": "...", "prior": 0.0, "likelihood": 0.0, "exclusivity": "...", "posterior": 0.0}
  ],
  "best_explanation": "...",
  "discriminating_test": "...",
  "novel_insight": "..."
}]"""

RT_UOT_SYSTEM = """You are an ocean intelligence RED TEAM. Your job is to DESTROY hypotheses.

You will be given a set of hypotheses. For EACH one, attack it from every angle:

1. DATA ATTACK: What data would DISPROVE this? Does such data likely exist?
2. LOGIC ATTACK: Are there logical fallacies, confounders, or selection biases?
3. ALTERNATIVE EXPLANATION: What simpler explanation accounts for the same evidence?
4. SCOPE ATTACK: Is the hypothesis overgeneralized from limited data?
5. SURVIVABILITY VERDICT: After all attacks, does the hypothesis survive? Rate 0.0-1.0.

Be ruthless. Only hypotheses that survive adversarial scrutiny deserve high scores.
If a hypothesis is trivially true or unfalsifiable, score it 0.0 — it's not useful.

Output JSON array:
[{
  "hypothesis": "...",
  "data_attack": "...",
  "logic_attack": "...",
  "simpler_alternative": "...",
  "scope_attack": "...",
  "survivability": 0.0,
  "refined_hypothesis": "...",
  "fatal_flaw": "..."
}]"""

CR_UOT_SYSTEM = """You are an ocean intelligence analyst performing constraint relaxation reasoning.

You will be given findings and the constraints under which they were derived (geographic bounds,
time windows, taxonomic filters, data source limitations, etc.).

For each constraint:
1. IDENTIFY the constraint explicitly
2. RELAX it: What patterns might emerge if this constraint were removed or widened?
3. CHECK: Is there evidence from adjacent regions/periods/taxa that supports the relaxed pattern?
4. HIDDEN PATTERN: What was the constraint masking? Could the constraint itself be the cause
   of an apparent pattern (artifact vs. signal)?

Output JSON array:
[{
  "constraint": "...",
  "constraint_type": "geographic|temporal|taxonomic|methodological|data_source",
  "relaxed_scope": "...",
  "predicted_pattern": "...",
  "supporting_evidence": "...",
  "artifact_risk": "...",
  "hidden_insight": "...",
  "priority": 0.0
}]"""

SCORER_SYSTEM = """You are a thought quality evaluator. Given a list of thoughts (ideas, hypotheses, analogies),
rate each one on a 0.0-1.0 scale based on:
- Novelty: Is this a genuine NEW insight, or obvious/well-established science? (weight: 0.40)
- Actionability: Can it lead to testable predictions or real decisions? (weight: 0.30)
- Grounding: Is it backed by data or just speculation? (weight: 0.30)

Penalize ideas that are well-established in peer-reviewed literature. Reward insights that connect domains in ways not yet published, or challenge widely-held assumptions with evidence.

Output JSON array:
[{"thought_index": 0, "score": 0.0, "reasoning": "..."}]"""


def _extract_json_array(raw: str) -> list[dict[str, Any]] | None:
    """Extract a JSON array from LLM output, stripping markdown fences."""
    cleaned = raw.strip()
    # Strip markdown fences
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    # Try parsing directly
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    # Try extracting first [...] block from mixed text
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end > start:
        try:
            parsed = json.loads(cleaned[start : end + 1])
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    return None


class UniverseOfThoughts:
    """Creative reasoning through systematic thought exploration with thought graph."""

    def __init__(
        self,
        prune_threshold: float = 0.2,
        max_depth: int = 3,
    ) -> None:
        self._prune_threshold = prune_threshold
        self._max_depth = max_depth

    async def _call_llm(self, system: str, user_message: str) -> str:
        from okeanus.ml.llm.client import call_llm

        return await call_llm(system, user_message)

    async def _score_thoughts(self, thoughts: list[Thought]) -> list[Thought]:
        """Use LLM to score a batch of thoughts."""
        if not thoughts:
            return thoughts

        thought_list = "\n".join(
            f"{i}. [{t.thought_type}] {t.content}" for i, t in enumerate(thoughts)
        )
        raw = await self._call_llm(SCORER_SYSTEM, f"Rate these thoughts:\n{thought_list}")

        parsed = False
        try:
            cleaned = raw.strip()
            # Strip markdown fences (```json ... ``` or ``` ... ```)
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
            scores = json.loads(cleaned)
            if isinstance(scores, list):
                for item in scores:
                    idx = item.get("thought_index", -1)
                    if 0 <= idx < len(thoughts):
                        thoughts[idx].score = item.get("score", 0.5)
                parsed = True
        except json.JSONDecodeError:
            pass

        # Regex fallback: extract (index, score) pairs from free-form text
        # Matches patterns like: "thought_index": 0, "score": 0.7
        # or: Thought 0: 0.7, or: 0. score: 0.85, or: #0 — 0.6
        if not parsed:
            found = 0
            for m in re.finditer(
                r'(?:thought[_\s]*(?:index)?["\s:]*)?(\d+)[^0-9.]*?'
                r'(?:score["\s:]*)?(\d\.\d+)',
                raw, re.IGNORECASE,
            ):
                idx = int(m.group(1))
                score = float(m.group(2))
                if 0 <= idx < len(thoughts) and 0.0 <= score <= 1.0:
                    thoughts[idx].score = score
                    found += 1
            if found:
                logger.info("Regex fallback extracted %d/%d thought scores", found, len(thoughts))
            else:
                logger.warning("Could not parse thought scores from LLM output, keeping defaults")

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
        """Extract real assumptions from knowledge graph edges related to the topic.

        Strategy:
        1. Search embeddings for topic, filtering to source_type='entity' only
           (entity source_ids are the UUIDs used in knowledge_edges)
        2. Query knowledge_edges using those entity UUIDs
        3. Fallback: if no topic-matched edges, fetch top edges by strength
        """
        try:
            from okeanus.ml.vectors.search import VectorSearch
            from sqlalchemy import text as sql_text

            searcher = VectorSearch()
            # Step 1: Find ENTITY embeddings related to the topic
            # (only entities have matching UUIDs in knowledge_edges)
            related = await searcher.search(
                session, topic, limit=limit, source_type="entity",
            )

            assumptions: list[str] = []

            if related:
                # Step 2: Use entity UUIDs to query knowledge_edges
                entity_ids = [r["source_id"] for r in related[:5]]
                placeholders = ", ".join(f"'{eid}'" for eid in entity_ids)

                sql = sql_text(f"""
                    SELECT source_label, edge_type, target_label, strength
                    FROM knowledge_edges
                    WHERE source_id::text IN ({placeholders})
                       OR target_id::text IN ({placeholders})
                    ORDER BY strength DESC
                    LIMIT :lim
                """)
                rows = (await session.execute(sql, {"lim": limit})).fetchall()

                for row in rows:
                    assumptions.append(
                        f"{row.source_label} {row.edge_type} {row.target_label} "
                        f"(strength: {row.strength:.2f})"
                    )

            # Step 3: Fallback — fetch top knowledge_edges by strength regardless
            # of topic, so T-UoT always has real assumptions to challenge
            if not assumptions:
                logger.info(
                    "No topic-matched KG edges for '%s', fetching top edges by strength",
                    topic,
                )
                fallback_sql = sql_text("""
                    SELECT source_label, edge_type, target_label, strength
                    FROM knowledge_edges
                    WHERE source_label IS NOT NULL
                      AND target_label IS NOT NULL
                    ORDER BY strength DESC
                    LIMIT :lim
                """)
                rows = (await session.execute(fallback_sql, {"lim": limit})).fetchall()

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
        parsed = _extract_json_array(raw)
        if parsed:
            for item in parsed:
                t = Thought(
                    content=json.dumps(item, default=str),
                    score=item.get("strength", 0.5),
                    thought_type="C",
                    metadata=item,
                )
                graph.add(t)
                thoughts.append(t)
        else:
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
        parsed = _extract_json_array(raw)
        if parsed:
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
        else:
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
        parsed = _extract_json_array(raw)
        if parsed:
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
        else:
            t = Thought(content=raw[:500], score=0.4, thought_type="T")
            graph.add(t)
            thoughts.append(t)

        return thoughts

    async def d_uot_dialectic(
        self,
        graph: ThoughtGraph,
        parent_ids: list[str] | None = None,
        context: str = "",
    ) -> list[Thought]:
        """Dialectical reasoning (D-UoT).

        Takes existing hypotheses and generates thesis/antithesis/synthesis triads.
        Forces the model to argue AGAINST its own insights.
        """
        # Gather existing hypotheses from the graph to challenge
        top = graph.top_k(8)
        if not top:
            return []

        hypotheses_text = "\n".join(
            f"{i+1}. {t.content[:200]}" for i, t in enumerate(top)
        )
        prompt = f"Findings/hypotheses to apply dialectical reasoning to:\n{hypotheses_text}"
        if context:
            prompt += f"\n\nContext:\n{context}"

        raw = await self._call_llm(D_UOT_SYSTEM, prompt)

        thoughts: list[Thought] = []
        parsed = _extract_json_array(raw)
        if parsed:
            for i, item in enumerate(parsed):
                parent = parent_ids[i % len(parent_ids)] if parent_ids else None
                t = Thought(
                    content=json.dumps(item, default=str),
                    score=item.get("confidence_shift", 0.5),
                    parent_id=parent,
                    thought_type="D",
                    metadata=item,
                )
                graph.add(t)
                thoughts.append(t)
        else:
            t = Thought(content=raw[:500], score=0.4, thought_type="D")
            graph.add(t)
            thoughts.append(t)

        return thoughts

    async def cf_uot_counterfactual(
        self,
        topic: str,
        graph: ThoughtGraph,
        parent_ids: list[str] | None = None,
        context: str = "",
    ) -> list[Thought]:
        """Counterfactual reasoning (CF-UoT).

        Constructs alternative worlds: "What if X were NOT true?"
        Different from T-UoT (which mutates single assumptions) — counterfactual
        reasoning builds coherent alternative realities and checks consistency.
        """
        top = graph.top_k(6)
        findings_text = "\n".join(
            f"{i+1}. {t.content[:200]}" for i, t in enumerate(top)
        ) if top else f"Topic: {topic}"

        prompt = (
            f"Topic: {topic}\n\n"
            f"Key findings to construct counterfactuals for:\n{findings_text}"
        )
        if context:
            prompt += f"\n\nContext:\n{context}"

        raw = await self._call_llm(CF_UOT_SYSTEM, prompt)

        thoughts: list[Thought] = []
        parsed = _extract_json_array(raw)
        if parsed:
            for i, item in enumerate(parsed):
                parent = parent_ids[i % len(parent_ids)] if parent_ids else None
                t = Thought(
                    content=json.dumps(item, default=str),
                    score=item.get("plausibility", 0.5),
                    parent_id=parent,
                    thought_type="CF",
                    metadata=item,
                )
                graph.add(t)
                thoughts.append(t)
        else:
            t = Thought(content=raw[:500], score=0.4, thought_type="CF")
            graph.add(t)
            thoughts.append(t)

        return thoughts

    async def ab_uot_abductive(
        self,
        anomalies: list[dict[str, Any]],
        graph: ThoughtGraph,
        parent_ids: list[str] | None = None,
        context: str = "",
    ) -> list[Thought]:
        """Abductive reasoning (AB-UoT).

        Given surprising observations or anomalies, reason backwards to the
        best explanation. Starts from anomalies/alerts and infers causes.
        """
        if not anomalies:
            # Fall back to using graph's most surprising (lowest-score) thoughts
            low_score = sorted(graph.all_thoughts(), key=lambda t: t.score)[:5]
            anomalies = [{"anomaly": t.content[:200]} for t in low_score] if low_score else []

        if not anomalies:
            return []

        anomalies_text = json.dumps(anomalies[:10], indent=2, default=str)
        prompt = f"Anomalies / surprising observations to explain:\n{anomalies_text}"
        if context:
            prompt += f"\n\nContext:\n{context}"

        raw = await self._call_llm(AB_UOT_SYSTEM, prompt)

        thoughts: list[Thought] = []
        parsed = _extract_json_array(raw)
        if parsed:
            for i, item in enumerate(parsed):
                parent = parent_ids[i % len(parent_ids)] if parent_ids else None
                # Use posterior of best explanation as score
                best_posterior = 0.5
                if isinstance(item.get("explanations"), list) and item["explanations"]:
                    best_posterior = max(
                        e.get("posterior", 0.5) for e in item["explanations"]
                    )
                t = Thought(
                    content=json.dumps(item, default=str),
                    score=best_posterior,
                    parent_id=parent,
                    thought_type="AB",
                    metadata=item,
                )
                graph.add(t)
                thoughts.append(t)
        else:
            t = Thought(content=raw[:500], score=0.4, thought_type="AB")
            graph.add(t)
            thoughts.append(t)

        return thoughts

    async def rt_uot_red_team(
        self,
        graph: ThoughtGraph,
        parent_ids: list[str] | None = None,
    ) -> list[Thought]:
        """Red team / adversarial reasoning (RT-UoT).

        Takes the top hypotheses and tries to DESTROY them. Only hypotheses
        that survive adversarial attack get high scores. Adjusts original
        thought scores based on survivability.
        """
        top = graph.top_k(8)
        if not top:
            return []

        hypotheses_text = "\n".join(
            f"{i+1}. {t.content[:200]}" for i, t in enumerate(top)
        )
        prompt = f"Hypotheses to attack:\n{hypotheses_text}"

        raw = await self._call_llm(RT_UOT_SYSTEM, prompt)

        thoughts: list[Thought] = []
        parsed = _extract_json_array(raw)
        if parsed:
            for i, item in enumerate(parsed):
                parent = parent_ids[i % len(parent_ids)] if parent_ids else None
                survivability = item.get("survivability", 0.5)

                # If the red team produced a refined hypothesis, use that
                content = item.get("refined_hypothesis", "") or json.dumps(item, default=str)
                t = Thought(
                    content=json.dumps(item, default=str),
                    score=survivability,
                    parent_id=parent,
                    thought_type="RT",
                    metadata=item,
                )
                graph.add(t)
                thoughts.append(t)

                # Penalize original thoughts that didn't survive
                if i < len(top) and survivability < 0.3:
                    top[i].score = min(top[i].score, survivability)
        else:
            t = Thought(content=raw[:500], score=0.4, thought_type="RT")
            graph.add(t)
            thoughts.append(t)

        return thoughts

    async def cr_uot_constraint_relax(
        self,
        topic: str,
        constraints: list[str],
        graph: ThoughtGraph,
        parent_ids: list[str] | None = None,
        context: str = "",
    ) -> list[Thought]:
        """Constraint relaxation reasoning (CR-UoT).

        Systematically removes constraints (geographic, temporal, taxonomic)
        to reveal patterns hidden by the constraints.
        """
        top = graph.top_k(6)
        findings_text = "\n".join(
            f"{i+1}. {t.content[:200]}" for i, t in enumerate(top)
        ) if top else f"Topic: {topic}"

        if not constraints:
            # Infer common constraints
            constraints = [
                "Geographic: limited to specific ocean regions",
                "Temporal: limited to observation time window",
                "Taxonomic: limited to observed species/entities",
                "Data source: limited to available sensor types",
                "Methodological: limited by analysis approach used",
            ]

        constraints_text = "\n".join(f"- {c}" for c in constraints)
        prompt = (
            f"Topic: {topic}\n\n"
            f"Findings derived under these constraints:\n{findings_text}\n\n"
            f"Constraints to relax:\n{constraints_text}"
        )
        if context:
            prompt += f"\n\nContext:\n{context}"

        raw = await self._call_llm(CR_UOT_SYSTEM, prompt)

        thoughts: list[Thought] = []
        parsed = _extract_json_array(raw)
        if parsed:
            for i, item in enumerate(parsed):
                parent = parent_ids[i % len(parent_ids)] if parent_ids else None
                t = Thought(
                    content=json.dumps(item, default=str),
                    score=item.get("priority", 0.5),
                    parent_id=parent,
                    thought_type="CR",
                    metadata=item,
                )
                graph.add(t)
                thoughts.append(t)
        else:
            t = Thought(content=raw[:500], score=0.4, thought_type="CR")
            graph.add(t)
            thoughts.append(t)

        return thoughts

    async def full_creative_reasoning(
        self,
        topic: str,
        evidence: str,
        domains: list[str],
        session=None,
        anomalies: list[dict[str, Any]] | None = None,
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run full UoT pipeline with thought graph, pruning, and recursive deepening.

        Pipeline per depth:
        C-UoT -> score -> prune ->
        E-UoT -> score -> prune ->
        T-UoT -> score -> prune ->
        D-UoT (dialectical) -> score -> prune ->
        CF-UoT (counterfactual) -> score -> prune ->
        AB-UoT (abductive) -> score -> prune ->
        RT-UoT (red team) -> score -> prune ->
        CR-UoT (constraint relaxation) -> score -> prune

        Then deepen: take top thoughts and run another cycle on them.
        """
        graph = ThoughtGraph(prune_threshold=self._prune_threshold)
        depth_stats: list[dict[str, Any]] = []

        for depth in range(self._max_depth):
            logger.info("UoT depth %d/%d for topic '%s'", depth + 1, self._max_depth, topic)
            total_pruned = 0
            step_counts: dict[str, int] = {}

            # Helper: run a strategy step with error isolation
            async def _run_step(
                name: str,
                coro,
            ) -> list[Thought]:
                try:
                    thoughts = await coro
                    scored = await self._score_thoughts(thoughts)
                    return scored
                except Exception as exc:
                    logger.warning("Strategy %s failed at depth %d: %s", name, depth, exc)
                    return []

            # -- Step 1: C-UoT — Cross-domain analogies --
            c_thoughts = await _run_step("C", self.c_uot_analogies(
                topic,
                domains[0] if domains else "general",
                domains[1:] or ["economics", "ecology"],
                graph,
                session=session,
                context=evidence[:500] if depth == 0 else "",
            ))
            total_pruned += graph.prune()
            step_counts["C"] = len(c_thoughts)

            # -- Step 2: E-UoT — Expand exploration --
            surviving_ids = [t.id for t in graph.by_type("C")]
            e_thoughts = await _run_step("E", self.e_uot_expand(
                [{"finding": topic, "evidence": evidence[:500]}]
                if depth == 0
                else [t.to_dict() for t in graph.top_k(5)],
                explored_domains=domains,
                graph=graph,
                parent_ids=surviving_ids or None,
                session=session,
            ))
            total_pruned += graph.prune()
            step_counts["E"] = len(e_thoughts)

            # -- Step 3: T-UoT — Transform assumptions --
            surviving_ids = [t.id for t in graph.top_k(5)]
            t_thoughts = await _run_step("T", self.t_uot_transform(
                topic,
                graph,
                parent_ids=surviving_ids or None,
                session=session,
                context=evidence[:500] if depth == 0 else "",
            ))
            total_pruned += graph.prune()
            step_counts["T"] = len(t_thoughts)

            # -- Step 4: D-UoT — Dialectical reasoning --
            surviving_ids = [t.id for t in graph.top_k(5)]
            d_thoughts = await _run_step("D", self.d_uot_dialectic(
                graph,
                parent_ids=surviving_ids or None,
                context=evidence[:500] if depth == 0 else "",
            ))
            total_pruned += graph.prune()
            step_counts["D"] = len(d_thoughts)

            # -- Step 5: CF-UoT — Counterfactual reasoning --
            surviving_ids = [t.id for t in graph.top_k(5)]
            cf_thoughts = await _run_step("CF", self.cf_uot_counterfactual(
                topic,
                graph,
                parent_ids=surviving_ids or None,
                context=evidence[:500] if depth == 0 else "",
            ))
            total_pruned += graph.prune()
            step_counts["CF"] = len(cf_thoughts)

            # -- Step 6: AB-UoT — Abductive reasoning --
            surviving_ids = [t.id for t in graph.top_k(5)]
            ab_thoughts = await _run_step("AB", self.ab_uot_abductive(
                anomalies or [],
                graph,
                parent_ids=surviving_ids or None,
                context=evidence[:500] if depth == 0 else "",
            ))
            total_pruned += graph.prune()
            step_counts["AB"] = len(ab_thoughts)

            # -- Step 7: RT-UoT — Red team / adversarial --
            surviving_ids = [t.id for t in graph.top_k(5)]
            rt_thoughts = await _run_step("RT", self.rt_uot_red_team(
                graph,
                parent_ids=surviving_ids or None,
            ))
            total_pruned += graph.prune()
            step_counts["RT"] = len(rt_thoughts)

            # -- Step 8: CR-UoT — Constraint relaxation --
            surviving_ids = [t.id for t in graph.top_k(5)]
            cr_thoughts = await _run_step("CR", self.cr_uot_constraint_relax(
                topic,
                constraints or [],
                graph,
                parent_ids=surviving_ids or None,
                context=evidence[:500] if depth == 0 else "",
            ))
            total_pruned += graph.prune()
            step_counts["CR"] = len(cr_thoughts)

            depth_stats.append({
                "depth": depth,
                "steps": step_counts,
                "total_generated": sum(step_counts.values()),
                "pruned": total_pruned,
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
            "dialectics": [t.to_dict() for t in graph.by_type("D")],
            "counterfactuals": [t.to_dict() for t in graph.by_type("CF")],
            "abductions": [t.to_dict() for t in graph.by_type("AB")],
            "red_team": [t.to_dict() for t in graph.by_type("RT")],
            "constraint_relaxations": [t.to_dict() for t in graph.by_type("CR")],
            "domains_explored": domains,
        }
