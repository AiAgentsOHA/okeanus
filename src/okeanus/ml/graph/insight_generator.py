"""UoT-powered insight generation from knowledge graph structure.

Runs the 8-step Universe of Thoughts pipeline on graph communities and
bridge nodes to produce stored intelligence insights.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class InsightGenerator:
    """Run UoT 8-step pipeline on graph communities to generate intelligence."""

    def __init__(self, max_communities: int = 5, max_bridges: int = 10) -> None:
        self._max_communities = max_communities
        self._max_bridges = max_bridges

    async def generate_all(
        self,
        session: AsyncSession,
        nx_engine: Any,
    ) -> dict[str, Any]:
        """Run insight generation on communities and bridges.

        Returns summary of generated insights.
        """
        results: dict[str, Any] = {
            "community_insights": 0,
            "bridge_insights": 0,
            "total": 0,
            "errors": [],
        }

        # Generate community insights
        try:
            comm_count = await self._generate_community_insights(session, nx_engine)
            results["community_insights"] = comm_count
            results["total"] += comm_count
        except Exception as exc:
            logger.warning("Community insight generation failed: %s", exc)
            results["errors"].append(f"community: {exc}")

        # Generate bridge insights
        try:
            bridge_count = await self._generate_bridge_insights(session, nx_engine)
            results["bridge_insights"] = bridge_count
            results["total"] += bridge_count
        except Exception as exc:
            logger.warning("Bridge insight generation failed: %s", exc)
            results["errors"].append(f"bridge: {exc}")

        await session.commit()
        return results

    async def _generate_community_insights(
        self,
        session: AsyncSession,
        nx_engine: Any,
    ) -> int:
        """For top communities, build topic + evidence and run UoT."""
        from okeanus.ml.synthesis.insights import InsightManager
        from okeanus.ml.synthesis.uot import UniverseOfThoughts

        uot = UniverseOfThoughts(prune_threshold=0.3, max_depth=1)
        mgr = InsightManager()
        count = 0

        sizes = nx_engine._metrics.get("community_sizes", {})
        top_communities = sorted(sizes.items(), key=lambda x: -x[1])[
            : self._max_communities
        ]

        for cid, size in top_communities:
            if size < 5:
                continue

            summary = nx_engine.get_community_summary(cid)
            entity_types = summary.get("entity_types", {})
            sources = summary.get("sources", {})
            domains = list(entity_types.keys())[:6]

            topic = (
                f"Community {cid} ({size} entities): "
                f"Dominated by {', '.join(f'{t}({c})' for t, c in list(entity_types.items())[:4])}. "
                f"Sources: {', '.join(list(sources.keys())[:5])}"
            )

            evidence = (
                f"Entity types: {entity_types}. "
                f"Data sources: {sources}. "
                f"Size: {size} members."
            )

            try:
                result = await uot.full_creative_reasoning(
                    topic=topic,
                    evidence=evidence,
                    domains=domains,
                    session=session,
                )

                # Extract top thoughts and store as insights
                thoughts = result.get("top_thoughts", [])
                for thought in thoughts[:3]:
                    content = thought.get("content", "")
                    score = thought.get("score", 0.5)
                    thought_type = thought.get("type", "C")

                    if not content or score < 0.4:
                        continue

                    insight_type = _map_thought_type(thought_type)
                    insight = await mgr.create_insight(
                        session,
                        insight_type=insight_type,
                        title=_extract_title(content),
                        description=content[:4000],
                        confidence=score,
                        involved_domains=domains,
                        generator=f"UoT-{thought_type}-community-{cid}",
                        evidence={
                            "community_id": cid,
                            "community_size": size,
                            "entity_types": entity_types,
                            "sources": list(sources.keys())[:10],
                            "thought_types": list(result.get("depth_stats", [{}])[0].get("step_counts", {}).keys()) if result.get("depth_stats") else [],
                        },
                    )
                    count += 1

                    # Wire reasoning traces — capture UoT provenance
                    await mgr.add_trace(
                        session, insight.id,
                        phase=f"uot_{thought_type}",
                        input_text=f"Topic: {topic}\nEvidence: {evidence}",
                        output_text=content[:4000],
                    )
                    # Store depth stats as pipeline trace
                    depth_stats = result.get("depth_stats", [])
                    if depth_stats:
                        import json as _json
                        await mgr.add_trace(
                            session, insight.id,
                            phase="uot_pipeline",
                            input_text=f"Community {cid}, {size} entities, {len(domains)} domains",
                            output_text=_json.dumps(depth_stats)[:4000],
                        )

                logger.info(
                    "Generated %d insights for community %d (%d entities)",
                    min(len(thoughts), 3),
                    cid,
                    size,
                )
            except Exception as exc:
                logger.warning("UoT failed for community %d: %s", cid, exc)

        return count

    async def _generate_bridge_insights(
        self,
        session: AsyncSession,
        nx_engine: Any,
    ) -> int:
        """For top bridge nodes, run counterfactual + dialectical UoT."""
        from okeanus.ml.synthesis.insights import InsightManager
        from okeanus.ml.synthesis.uot import UniverseOfThoughts

        uot = UniverseOfThoughts(prune_threshold=0.3, max_depth=1)
        mgr = InsightManager()
        count = 0

        bridges = nx_engine.get_bridges(self._max_bridges)

        for bridge in bridges:
            label = bridge.get("label", "unknown")
            domain = bridge.get("domain", "")
            connected = bridge.get("connected_domains", [])
            score = bridge.get("score", 0)

            if len(connected) < 2:
                continue

            topic = (
                f"Bridge entity '{label}' ({domain}) connects "
                f"{len(connected)} domains: {', '.join(connected[:8])}"
            )

            evidence = (
                f"This entity bridges across {bridge.get('communities_bridged', 0)} communities. "
                f"Bridge score: {score}. Connected domains: {connected}."
            )

            constraints = [
                f"Entity is of type {domain}",
                f"Connects exactly these domains: {connected}",
            ]

            try:
                result = await uot.full_creative_reasoning(
                    topic=topic,
                    evidence=evidence,
                    domains=connected[:6] if connected else [domain],
                    session=session,
                    constraints=constraints,
                )

                thoughts = result.get("top_thoughts", [])
                for thought in thoughts[:2]:
                    content = thought.get("content", "")
                    t_score = thought.get("score", 0.5)
                    thought_type = thought.get("type", "CF")

                    if not content or t_score < 0.4:
                        continue

                    insight_type = _map_thought_type(thought_type)
                    insight = await mgr.create_insight(
                        session,
                        insight_type=insight_type,
                        title=_extract_title(content),
                        description=content[:4000],
                        confidence=t_score,
                        involved_domains=connected[:10],
                        generator=f"UoT-{thought_type}-bridge-{bridge.get('id', '')[:8]}",
                        evidence={
                            "bridge_id": bridge.get("id"),
                            "bridge_label": label,
                            "bridge_domain": domain,
                            "connected_domains": connected,
                            "bridge_score": score,
                            "thought_types": list(result.get("depth_stats", [{}])[0].get("step_counts", {}).keys()) if result.get("depth_stats") else [],
                        },
                    )
                    count += 1

                    # Wire reasoning traces — capture UoT provenance
                    await mgr.add_trace(
                        session, insight.id,
                        phase=f"uot_{thought_type}",
                        input_text=f"Topic: {topic}\nEvidence: {evidence}",
                        output_text=content[:4000],
                    )
                    depth_stats = result.get("depth_stats", [])
                    if depth_stats:
                        import json as _json
                        await mgr.add_trace(
                            session, insight.id,
                            phase="uot_pipeline",
                            input_text=f"Bridge '{label}', {len(connected)} domains",
                            output_text=_json.dumps(depth_stats)[:4000],
                        )

                logger.info(
                    "Generated %d insights for bridge '%s'",
                    min(len(thoughts), 2),
                    label[:50],
                )
            except Exception as exc:
                logger.warning("UoT failed for bridge '%s': %s", label[:50], exc)

        return count


def _extract_title(content: str, max_len: int = 250) -> str:
    """Extract a clean title from UoT thought content (may be JSON)."""
    import json as _json
    try:
        obj = _json.loads(content)
        if isinstance(obj, dict):
            # Try common keys for a short summary
            for key in ("insight", "summary", "finding", "constraint", "original_finding",
                        "original_assumption", "thesis", "hypothesis"):
                if key in obj:
                    return str(obj[key])[:max_len]
            # Fallback: first string value
            for v in obj.values():
                if isinstance(v, str) and len(v) > 10:
                    return v[:max_len]
    except (_json.JSONDecodeError, TypeError):
        pass
    return content[:max_len]


def _map_thought_type(thought_type: str) -> str:
    """Map UoT thought type to InsightType enum value."""
    mapping = {
        "C": "bridge_concept",       # Cross-domain analogy
        "E": "emergent_pattern",     # Exploratory
        "T": "causal_hypothesis",    # Transformational
        "D": "bridge_concept",       # Dialectical synthesis
        "CF": "causal_hypothesis",   # Counterfactual
        "AB": "anomaly_cluster",     # Abductive
        "RT": "causal_hypothesis",   # Red team survived
        "CR": "emergent_pattern",    # Constraint relaxation
    }
    return mapping.get(thought_type, "emergent_pattern")
