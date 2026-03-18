"""NetworkX graph algorithms for knowledge graph analysis.

Provides betweenness centrality, community detection, and structural
hole discovery for cross-domain bridge concept identification.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import networkx as nx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class GraphAlgorithms:
    """Run graph algorithms over the knowledge graph."""

    async def _load_graph(
        self,
        session: AsyncSession,
        domain: str | None = None,
        max_nodes: int = 10000,
    ) -> nx.DiGraph:
        """Load knowledge_edges into a NetworkX directed graph."""
        params: dict[str, Any] = {"lim": max_nodes}
        domain_filter = ""
        if domain:
            domain_filter = "WHERE domain = :domain"
            params["domain"] = domain

        sql = text(f"""
            SELECT source_id, source_type, source_label,
                   target_id, target_type, target_label,
                   edge_type, strength, domain
            FROM knowledge_edges
            {domain_filter}
            LIMIT :lim
        """)
        rows = (await session.execute(sql, params)).fetchall()

        G = nx.DiGraph()
        for row in rows:
            src = str(row.source_id)
            tgt = str(row.target_id)
            G.add_node(src, type=row.source_type, label=row.source_label or src[:8],
                       domain=row.domain)
            G.add_node(tgt, type=row.target_type, label=row.target_label or tgt[:8],
                       domain=row.domain)
            G.add_edge(src, tgt, edge_type=row.edge_type,
                       weight=row.strength, domain=row.domain)
        return G

    async def betweenness_centrality(
        self,
        session: AsyncSession,
        domain: str | None = None,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Find the most central nodes (bridge concepts) via betweenness centrality.

        Nodes with high betweenness sit on many shortest paths — they are
        the concepts that connect otherwise-separate clusters.
        """
        G = await self._load_graph(session, domain=domain)
        if not G.nodes:
            return []

        bc = nx.betweenness_centrality(G, weight="weight", normalized=True)
        ranked = sorted(bc.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return [
            {
                "node_id": node_id,
                "label": G.nodes[node_id].get("label", ""),
                "type": G.nodes[node_id].get("type", ""),
                "domain": G.nodes[node_id].get("domain", ""),
                "betweenness": round(score, 6),
                "degree": G.degree(node_id),
            }
            for node_id, score in ranked
        ]

    async def detect_communities(
        self,
        session: AsyncSession,
        domain: str | None = None,
        resolution: float = 1.0,
    ) -> list[dict[str, Any]]:
        """Detect communities using Louvain algorithm on the undirected projection.

        Returns communities sorted by size, with member node info.
        """
        G_directed = await self._load_graph(session, domain=domain)
        if not G_directed.nodes:
            return []

        G = G_directed.to_undirected()

        communities = nx.community.louvain_communities(
            G, weight="weight", resolution=resolution, seed=42
        )

        result = []
        for i, comm in enumerate(sorted(communities, key=len, reverse=True)):
            members = []
            domains_seen = set()
            for node_id in list(comm)[:50]:  # cap display
                node_data = G.nodes[node_id]
                members.append({
                    "node_id": node_id,
                    "label": node_data.get("label", ""),
                    "type": node_data.get("type", ""),
                    "domain": node_data.get("domain", ""),
                })
                if node_data.get("domain"):
                    domains_seen.add(node_data["domain"])

            result.append({
                "community_id": i,
                "size": len(comm),
                "domains": sorted(domains_seen),
                "is_cross_domain": len(domains_seen) > 1,
                "members": members,
            })

        return result

    async def structural_holes(
        self,
        session: AsyncSession,
        domain: str | None = None,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Find structural holes — nodes that bridge sparse connections.

        Uses Burt's constraint measure: lower constraint = more structural holes
        (the node bridges disconnected groups).
        """
        G_directed = await self._load_graph(session, domain=domain)
        if not G_directed.nodes:
            return []

        G = G_directed.to_undirected()

        try:
            constraint = nx.constraint(G, weight="weight")
        except Exception:
            # Fallback if constraint computation fails
            constraint = {}
            for node in G.nodes:
                if G.degree(node) > 0:
                    constraint[node] = 1.0 / G.degree(node)

        # Lower constraint = better bridge position
        ranked = sorted(
            [(n, c) for n, c in constraint.items() if c is not None and c > 0],
            key=lambda x: x[1],
        )[:top_k]

        return [
            {
                "node_id": node_id,
                "label": G.nodes[node_id].get("label", ""),
                "type": G.nodes[node_id].get("type", ""),
                "domain": G.nodes[node_id].get("domain", ""),
                "constraint": round(score, 6),
                "degree": G.degree(node_id),
                "neighbors_domains": sorted(set(
                    G.nodes[n].get("domain", "") for n in G.neighbors(node_id)
                    if G.nodes[n].get("domain")
                )),
            }
            for node_id, score in ranked
        ]

    async def cross_domain_bridges(
        self,
        session: AsyncSession,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Find nodes that connect entities across different domains.

        Combines betweenness centrality with cross-domain edge analysis.
        """
        G = await self._load_graph(session)
        if not G.nodes:
            return []

        scores: dict[str, float] = {}
        for node in G.nodes:
            neighbor_domains = set()
            for n in G.predecessors(node):
                d = G.nodes[n].get("domain")
                if d:
                    neighbor_domains.add(d)
            for n in G.successors(node):
                d = G.nodes[n].get("domain")
                if d:
                    neighbor_domains.add(d)

            if len(neighbor_domains) > 1:
                scores[node] = len(neighbor_domains) * G.degree(node)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return [
            {
                "node_id": node_id,
                "label": G.nodes[node_id].get("label", ""),
                "type": G.nodes[node_id].get("type", ""),
                "domain": G.nodes[node_id].get("domain", ""),
                "cross_domain_score": score,
                "degree": G.degree(node_id),
                "connected_domains": sorted(set(
                    G.nodes[n].get("domain", "")
                    for n in list(G.predecessors(node_id)) + list(G.successors(node_id))
                    if G.nodes[n].get("domain")
                )),
            }
            for node_id, score in ranked
        ]

    async def graph_summary(self, session: AsyncSession) -> dict[str, Any]:
        """Return overall graph statistics."""
        G = await self._load_graph(session)
        if not G.nodes:
            return {"nodes": 0, "edges": 0, "density": 0}

        domains = set()
        for _, data in G.nodes(data=True):
            if data.get("domain"):
                domains.add(data["domain"])

        return {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "density": round(nx.density(G), 6),
            "domains": sorted(domains),
            "is_connected": nx.is_weakly_connected(G) if G.number_of_nodes() > 0 else False,
            "components": nx.number_weakly_connected_components(G),
        }
