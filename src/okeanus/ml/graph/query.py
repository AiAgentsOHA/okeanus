"""Graph query engine using recursive CTEs."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.ml.graph.models import KnowledgeEdge


class GraphQueryEngine:
    """SQL-based graph traversal on the ``knowledge_edges`` table."""

    async def get_neighbors(
        self,
        session: AsyncSession,
        node_id: UUID,
        node_type: str = "entity",
        depth: int = 1,
        edge_types: list[str] | None = None,
    ) -> dict:
        """BFS neighbor traversal via recursive CTE.

        Returns ``{"nodes": [...], "edges": [...]}``.
        """
        depth = min(depth, 10)

        params: dict = {"node_id": str(node_id), "node_type": node_type, "max_depth": depth}

        edge_filter = ""
        if edge_types:
            placeholders = ", ".join(f":et{i}" for i in range(len(edge_types)))
            edge_filter = f"AND e.edge_type IN ({placeholders})"
            for i, et in enumerate(edge_types):
                params[f"et{i}"] = et

        sql = text(
            f"""
            WITH RECURSIVE neighbors AS (
                -- Seed: direct edges touching the start node
                SELECT
                    e.id AS edge_id,
                    e.source_id, e.source_type, e.source_label,
                    e.target_id, e.target_type, e.target_label,
                    e.edge_type, e.strength,
                    1 AS depth
                FROM knowledge_edges e
                WHERE ((e.source_id = :node_id AND e.source_type = :node_type)
                    OR (e.target_id = :node_id AND e.target_type = :node_type))
                {edge_filter}

                UNION ALL

                -- Recurse outward
                SELECT
                    e.id AS edge_id,
                    e.source_id, e.source_type, e.source_label,
                    e.target_id, e.target_type, e.target_label,
                    e.edge_type, e.strength,
                    n.depth + 1 AS depth
                FROM knowledge_edges e
                JOIN neighbors n
                  ON (e.source_id = n.target_id AND e.source_type = n.target_type
                      AND NOT (e.target_id = :node_id AND e.target_type = :node_type))
                  OR (e.target_id = n.source_id AND e.target_type = n.source_type
                      AND NOT (e.source_id = :node_id AND e.source_type = :node_type))
                WHERE n.depth < :max_depth
                {edge_filter}
            )
            SELECT DISTINCT
                edge_id, source_id, source_type, source_label,
                target_id, target_type, target_label,
                edge_type, strength, depth
            FROM neighbors
            ORDER BY depth, strength DESC
            """
        )

        rows = (await session.execute(sql, params)).fetchall()

        nodes_seen: dict[str, dict] = {}
        edges_out: list[dict] = []

        for row in rows:
            edges_out.append(
                {
                    "id": str(row.edge_id),
                    "source_id": str(row.source_id),
                    "source_type": row.source_type,
                    "target_id": str(row.target_id),
                    "target_type": row.target_type,
                    "edge_type": row.edge_type,
                    "strength": row.strength,
                    "depth": row.depth,
                }
            )
            for prefix in ("source", "target"):
                nid = str(getattr(row, f"{prefix}_id"))
                if nid not in nodes_seen:
                    nodes_seen[nid] = {
                        "id": nid,
                        "type": getattr(row, f"{prefix}_type"),
                        "label": getattr(row, f"{prefix}_label"),
                    }

        return {"nodes": list(nodes_seen.values()), "edges": edges_out}

    async def find_paths(
        self,
        session: AsyncSession,
        source_id: UUID,
        target_id: UUID,
        max_depth: int = 5,
    ) -> list[list[dict]]:
        """Find all paths between two nodes using recursive CTE.

        Returns a list of paths, each path being a list of edge dicts.
        """
        max_depth = min(max_depth, 10)
        sql = text(
            """
            WITH RECURSIVE paths AS (
                SELECT
                    e.id AS edge_id,
                    e.source_id, e.source_type,
                    e.target_id, e.target_type,
                    e.edge_type, e.strength,
                    ARRAY[e.id] AS path_ids,
                    ARRAY[e.source_id] AS visited,
                    1 AS depth
                FROM knowledge_edges e
                WHERE e.source_id = :source_id

                UNION ALL

                SELECT
                    e.id,
                    e.source_id, e.source_type,
                    e.target_id, e.target_type,
                    e.edge_type, e.strength,
                    p.path_ids || e.id,
                    p.visited || e.source_id,
                    p.depth + 1
                FROM knowledge_edges e
                JOIN paths p ON e.source_id = p.target_id
                WHERE p.depth < :max_depth
                  AND NOT (e.source_id = ANY(p.visited))
            )
            SELECT edge_id, source_id, source_type, target_id, target_type,
                   edge_type, strength, path_ids, depth
            FROM paths
            WHERE target_id = :target_id
            ORDER BY depth
            LIMIT 50
            """
        )

        rows = (
            await session.execute(
                sql,
                {
                    "source_id": str(source_id),
                    "target_id": str(target_id),
                    "max_depth": max_depth,
                },
            )
        ).fetchall()

        # Each row represents the final edge of a complete path.
        # Fetch full path edges from path_ids.
        all_paths: list[list[dict]] = []
        for row in rows:
            path_edge_ids = row.path_ids
            if not path_edge_ids:
                continue
            edge_sql = text(
                """
                SELECT id, source_id, source_type, target_id, target_type,
                       edge_type, strength
                FROM knowledge_edges
                WHERE id = ANY(:ids)
                """
            )
            edge_rows = (
                await session.execute(edge_sql, {"ids": path_edge_ids})
            ).fetchall()

            # Reorder edges by path_ids order
            edge_map = {str(er.id): er for er in edge_rows}
            path: list[dict] = []
            for eid in path_edge_ids:
                er = edge_map.get(str(eid))
                if er:
                    path.append(
                        {
                            "id": str(er.id),
                            "source_id": str(er.source_id),
                            "source_type": er.source_type,
                            "target_id": str(er.target_id),
                            "target_type": er.target_type,
                            "edge_type": er.edge_type,
                            "strength": er.strength,
                        }
                    )
            all_paths.append(path)

        return all_paths

    async def get_subgraph(
        self,
        session: AsyncSession,
        node_ids: list[UUID],
        include_neighbors: bool = True,
    ) -> dict:
        """Extract a subgraph for NetworkX loading.

        Returns ``{"nodes": [{id, type, label, domain, ...}], "edges": [{source, target, type, strength, ...}]}``.
        """
        str_ids = [str(nid) for nid in node_ids]

        if include_neighbors:
            sql = text(
                """
                SELECT DISTINCT
                    id, source_id, source_type, source_label,
                    target_id, target_type, target_label,
                    edge_type, strength, domain
                FROM knowledge_edges
                WHERE source_id = ANY(:ids) OR target_id = ANY(:ids)
                """
            )
        else:
            sql = text(
                """
                SELECT DISTINCT
                    id, source_id, source_type, source_label,
                    target_id, target_type, target_label,
                    edge_type, strength, domain
                FROM knowledge_edges
                WHERE source_id = ANY(:ids) AND target_id = ANY(:ids)
                """
            )

        rows = (await session.execute(sql, {"ids": str_ids})).fetchall()

        nodes_seen: dict[str, dict] = {}
        edges_out: list[dict] = []

        for row in rows:
            edges_out.append(
                {
                    "source": str(row.source_id),
                    "target": str(row.target_id),
                    "type": row.edge_type,
                    "strength": row.strength,
                    "domain": row.domain,
                }
            )
            for prefix in ("source", "target"):
                nid = str(getattr(row, f"{prefix}_id"))
                if nid not in nodes_seen:
                    nodes_seen[nid] = {
                        "id": nid,
                        "type": getattr(row, f"{prefix}_type"),
                        "label": getattr(row, f"{prefix}_label"),
                        "domain": row.domain,
                    }

        return {"nodes": list(nodes_seen.values()), "edges": edges_out}

    async def cross_domain_bridges(
        self,
        session: AsyncSession,
        domain_a: str,
        domain_b: str,
        limit: int = 20,
    ) -> list[dict]:
        """Find nodes connected to both *domain_a* and *domain_b* entities.

        These are bridge concepts in Buehler's cross-domain framework.
        """
        sql = text(
            """
            WITH a_nodes AS (
                SELECT DISTINCT source_id AS node_id FROM knowledge_edges WHERE domain = :domain_a
                UNION
                SELECT DISTINCT target_id FROM knowledge_edges WHERE domain = :domain_a
            ),
            b_nodes AS (
                SELECT DISTINCT source_id AS node_id FROM knowledge_edges WHERE domain = :domain_b
                UNION
                SELECT DISTINCT target_id FROM knowledge_edges WHERE domain = :domain_b
            ),
            bridges AS (
                SELECT node_id FROM a_nodes
                INTERSECT
                SELECT node_id FROM b_nodes
            )
            SELECT
                ke.source_id, ke.source_type, ke.source_label,
                ke.target_id, ke.target_type, ke.target_label,
                ke.edge_type, ke.strength, ke.domain
            FROM knowledge_edges ke
            WHERE ke.source_id IN (SELECT node_id FROM bridges)
               OR ke.target_id IN (SELECT node_id FROM bridges)
            LIMIT :lim
            """
        )
        rows = (
            await session.execute(
                sql, {"domain_a": domain_a, "domain_b": domain_b, "lim": limit}
            )
        ).fetchall()

        return [
            {
                "source_id": str(row.source_id),
                "source_type": row.source_type,
                "source_label": row.source_label,
                "target_id": str(row.target_id),
                "target_type": row.target_type,
                "target_label": row.target_label,
                "edge_type": row.edge_type,
                "strength": row.strength,
                "domain": row.domain,
            }
            for row in rows
        ]

    async def edge_stats(self, session: AsyncSession) -> dict:
        """Return summary stats: total edges, by type, by node_type, avg strength."""
        total_result = await session.execute(
            select(func.count()).select_from(KnowledgeEdge)
        )
        total = total_result.scalar() or 0

        by_type_result = await session.execute(
            select(KnowledgeEdge.edge_type, func.count())
            .group_by(KnowledgeEdge.edge_type)
            .order_by(func.count().desc())
        )
        by_type = {row[0]: row[1] for row in by_type_result.fetchall()}

        by_node_result = await session.execute(
            select(KnowledgeEdge.source_type, func.count())
            .group_by(KnowledgeEdge.source_type)
            .order_by(func.count().desc())
        )
        by_node_type = {row[0]: row[1] for row in by_node_result.fetchall()}

        avg_result = await session.execute(
            select(func.avg(KnowledgeEdge.strength))
        )
        avg_strength = avg_result.scalar()

        return {
            "total_edges": total,
            "by_edge_type": by_type,
            "by_source_node_type": by_node_type,
            "avg_strength": round(float(avg_strength), 4) if avg_strength else 0.0,
        }
