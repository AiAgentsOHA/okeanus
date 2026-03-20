"""Cached NetworkX graph engine for full-graph analytics."""

from __future__ import annotations

import logging
import time
from typing import Any

import networkx as nx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Module-level singleton
_engine: NetworkXEngine | None = None


def get_engine() -> NetworkXEngine:
    global _engine
    if _engine is None:
        _engine = NetworkXEngine()
    return _engine


class NetworkXEngine:
    def __init__(self, ttl_seconds: float = 3600) -> None:
        self._graph: nx.Graph | None = None
        self._metrics: dict[str, Any] = {}
        self._built_at: float = 0
        self._ttl = ttl_seconds

    @property
    def is_stale(self) -> bool:
        return self._graph is None or time.time() - self._built_at > self._ttl

    async def ensure_built(self, session: AsyncSession) -> None:
        if not self.is_stale:
            return
        await self.rebuild(session)

    async def rebuild(self, session: AsyncSession) -> dict[str, int]:
        G = nx.Graph()

        # Load all entities as nodes
        rows = await session.execute(text("""
            SELECT id, name, entity_type, source_name, country, sector,
                   ST_Y(ST_Centroid(geometry::geometry)) as lat,
                   ST_X(ST_Centroid(geometry::geometry)) as lon
            FROM entities
        """))
        for r in rows.fetchall():
            G.add_node(str(r[0]), name=r[1], entity_type=r[2] or '',
                       source_name=r[3] or '', country=r[4] or '',
                       sector=r[5] or '', lat=r[6], lon=r[7])

        # Load all edges
        rows = await session.execute(text("""
            SELECT source_id, target_id, edge_type, strength,
                   source_label, target_label, source_type, target_type,
                   evidence_type
            FROM knowledge_edges
        """))
        for r in rows.fetchall():
            src, tgt = str(r[0]), str(r[1])
            if src not in G:
                G.add_node(src, name=r[4] or src[:8], entity_type=r[6] or '',
                           source_name='edge_ref')
            if tgt not in G:
                G.add_node(tgt, name=r[5] or tgt[:8], entity_type=r[7] or '',
                           source_name='edge_ref')
            G.add_edge(src, tgt, edge_type=r[2], weight=float(r[3]) if r[3] else 1.0,
                       evidence_type=r[8] or '')

        # Compute metrics
        logger.info("Computing NetworkX metrics for %d nodes, %d edges...",
                     G.number_of_nodes(), G.number_of_edges())

        pagerank = nx.pagerank(G, weight='weight', max_iter=100)
        degree_cent = nx.degree_centrality(G)

        # Sampled betweenness for performance
        n = G.number_of_nodes()
        k = min(500, n) if n > 500 else None
        betweenness = nx.betweenness_centrality(G, weight='weight', normalized=True, k=k)

        # Louvain communities
        communities = nx.community.louvain_communities(G, weight='weight',
                                                        resolution=1.0, seed=42)
        community_map: dict[str, int] = {}
        community_sizes: dict[int, int] = {}
        for i, comm in enumerate(sorted(communities, key=len, reverse=True)):
            community_sizes[i] = len(comm)
            for node_id in comm:
                community_map[node_id] = i

        # Find bridges
        bridges = self._find_bridges(G, community_map)

        self._graph = G
        self._metrics = {
            'pagerank': pagerank,
            'degree_centrality': degree_cent,
            'betweenness': betweenness,
            'community': community_map,
            'community_sizes': community_sizes,
            'bridges': bridges,
        }
        self._built_at = time.time()

        logger.info("NetworkX built: %d nodes, %d edges, %d communities, %d bridges",
                     G.number_of_nodes(), G.number_of_edges(),
                     len(community_sizes), len(bridges))

        return {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
                "components": nx.number_connected_components(G),
                "communities": len(community_sizes)}

    def _find_bridges(self, G: nx.Graph,
                      community_map: dict[str, int]) -> list[dict[str, Any]]:
        bridges: list[dict[str, Any]] = []
        for node in G.nodes:
            neighbor_comms: set[int] = set()
            neighbor_types: set[str] = set()
            for n in G.neighbors(node):
                if n in community_map:
                    neighbor_comms.add(community_map[n])
                ntype = G.nodes[n].get('entity_type', '')
                if ntype:
                    neighbor_types.add(ntype)
            if len(neighbor_comms) > 1 or len(neighbor_types) > 1:
                bridges.append({
                    'node_id': node,
                    'name': G.nodes[node].get('name', ''),
                    'entity_type': G.nodes[node].get('entity_type', ''),
                    'source_name': G.nodes[node].get('source_name', ''),
                    'communities_bridged': len(neighbor_comms),
                    'types_bridged': len(neighbor_types),
                    'degree': G.degree(node),
                    'score': len(neighbor_comms) * len(neighbor_types) * G.degree(node),
                })
        return sorted(bridges, key=lambda x: x['score'], reverse=True)[:200]

    def get_full_graph(self, entity_type: str | None = None,
                       community_id: int | None = None,
                       limit: int = 3000) -> dict[str, Any]:
        if not self._graph:
            return {"nodes": [], "edges": [], "communities": [], "summary": {}}

        G = self._graph
        pr = self._metrics.get('pagerank', {})
        dc = self._metrics.get('degree_centrality', {})
        cm = self._metrics.get('community', {})
        bridge_ids = {b['node_id'] for b in self._metrics.get('bridges', [])}

        # Filter and sort by pagerank
        node_list: list[tuple[str, float]] = []
        for nid in G.nodes:
            nd = G.nodes[nid]
            if entity_type and nd.get('entity_type', '') != entity_type:
                continue
            if community_id is not None and cm.get(nid) != community_id:
                continue
            node_list.append((nid, pr.get(nid, 0)))

        node_list.sort(key=lambda x: x[1], reverse=True)
        node_list = node_list[:limit]
        visible_ids = {nid for nid, _ in node_list}

        nodes: list[dict[str, Any]] = []
        for nid, _ in node_list:
            nd = G.nodes[nid]
            nodes.append({
                'id': nid,
                'name': nd.get('name', ''),
                'entity_type': nd.get('entity_type', ''),
                'source_name': nd.get('source_name', ''),
                'pagerank': round(pr.get(nid, 0), 8),
                'centrality': round(dc.get(nid, 0), 6),
                'community_id': cm.get(nid, -1),
                'is_bridge': nid in bridge_ids,
                'lat': nd.get('lat'),
                'lon': nd.get('lon'),
            })

        edges: list[dict[str, Any]] = []
        for u, v, data in G.edges(data=True):
            if u in visible_ids and v in visible_ids:
                edges.append({
                    'source': u, 'target': v,
                    'edge_type': data.get('edge_type', ''),
                    'weight': data.get('weight', 1.0),
                })

        cs = self._metrics.get('community_sizes', {})
        communities_out = [{'id': cid, 'size': size}
                           for cid, size in sorted(cs.items())[:50]]

        return {
            'nodes': nodes, 'edges': edges, 'communities': communities_out,
            'summary': {
                'total_nodes': G.number_of_nodes(),
                'total_edges': G.number_of_edges(),
                'communities': len(cs),
                'bridges': len(self._metrics.get('bridges', [])),
            }
        }

    def get_bridges(self, top_k: int = 50) -> list[dict[str, Any]]:
        bridges = self._metrics.get('bridges', [])
        result: list[dict[str, Any]] = []
        for b in bridges[:top_k]:
            nid = b['node_id']
            G = self._graph
            connected_domains: set[str] = set()
            if G:
                for n in G.neighbors(nid):
                    t = G.nodes[n].get('entity_type', '')
                    if t:
                        connected_domains.add(t)
            result.append({
                'id': nid,
                'label': b['name'],
                'domain': b['entity_type'],
                'connected_domains': list(connected_domains),
                'score': b['score'],
                'communities_bridged': b['communities_bridged'],
            })
        return result

    def get_community_summary(self, community_id: int) -> dict[str, Any]:
        if not self._graph:
            return {}
        cm = self._metrics.get('community', {})
        members = [nid for nid, cid in cm.items() if cid == community_id]
        G = self._graph
        types: dict[str, int] = {}
        sources: dict[str, int] = {}
        for nid in members:
            nd = G.nodes[nid]
            t = nd.get('entity_type', 'unknown')
            s = nd.get('source_name', 'unknown')
            types[t] = types.get(t, 0) + 1
            sources[s] = sources.get(s, 0) + 1
        return {
            'community_id': community_id,
            'size': len(members),
            'entity_types': dict(sorted(types.items(), key=lambda x: -x[1])),
            'sources': dict(sorted(sources.items(), key=lambda x: -x[1])[:10]),
            'top_members': members[:20],
        }
