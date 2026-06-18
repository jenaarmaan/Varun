from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import GraphNode, GraphEdge


class GraphRepository:
    """Graph Abstraction Layer to isolate PostGIS recursive traversals."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_node_by_id(self, node_id: str) -> Optional[GraphNode]:
        """Fetches a single node from the graph."""
        result = await self.db.execute(select(GraphNode).where(GraphNode.id == node_id))
        return result.scalars().first()

    async def get_downstream_infrastructure(self, reservoir_id: str) -> List[Dict[str, Any]]:
        """
        Executes a recursive CTE traversal query in PostgreSQL
        to find downstream elements affected by a reservoir node.
        """
        # Compiles recursive CTE query to trace downstream graph edges
        from sqlalchemy import text
        
        sql = text("""
            WITH RECURSIVE downstream_impacts AS (
                -- Anchor member
                SELECT id, type, name 
                FROM graph_nodes 
                WHERE id = :res_id
                UNION
                -- Recursive member
                SELECT n.id, n.type, n.name
                FROM graph_nodes n
                JOIN graph_edges e ON e.target_id = n.id
                JOIN downstream_impacts di ON di.id = e.source_id
                WHERE e.type IN ('downstream_of', 'affects')
            )
            SELECT id, type, name FROM downstream_impacts;
        """)
        
        result = await self.db.execute(sql, {"res_id": reservoir_id})
        rows = result.fetchall()
        
        return [
            {"id": row[0], "type": row[1], "name": row[2]}
            for row in rows
        ]

    async def get_district_elements(self, district_id: str) -> List[Dict[str, Any]]:
        """Finds all infrastructure located inside the district."""
        result = await self.db.execute(
            select(GraphNode)
            .join(GraphEdge, GraphEdge.source_id == GraphNode.id)
            .where(GraphEdge.target_id == district_id)
            .where(GraphEdge.type == "located_in")
        )
        nodes = result.scalars().all()
        return [
            {"id": n.id, "type": n.type, "name": n.name}
            for n in nodes
        ]


from typing import Optional
