import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.graph.builder import GraphNodeData
from backend.app.models import FileNode, GraphEdge, Symbol


class GraphPersistenceService:
    """Batch persists in-memory graph models to PostgreSQL / SQLite database."""

    async def persist_graph(
        self,
        db: AsyncSession,
        analysis_run_id: str,
        g: nx.MultiDiGraph,
    ) -> None:
        logger.info("Persisting graph data for analysis run %s...", analysis_run_id)

        file_node_id_map: dict[str, str] = {}  # rel_path -> db_id
        symbol_node_id_map: dict[str, str] = {}  # graph_node_id -> db_id

        # 1. Persist File Nodes
        for node_id, attrs in g.nodes(data=True):
            data: GraphNodeData = attrs.get("data")
            if not data or data.node_type != "file":
                continue

            file_db = FileNode(
                analysis_run_id=analysis_run_id,
                path=data.file_path or data.name,
                language=data.metadata.get("language", "Unknown"),
                loc=data.loc,
                blank_lines=data.blank_lines,
                comment_lines=data.comment_lines,
                cyclomatic_complexity=data.cyclomatic_complexity,
                afferent_coupling=data.fan_in,
                efferent_coupling=data.fan_out,
                instability=data.instability,
            )
            db.add(file_db)
            await db.flush()  # Populates file_db.id
            file_node_id_map[data.file_path] = file_db.id
            symbol_node_id_map[node_id] = file_db.id

        # 2. Persist Symbols (Classes, Functions, Methods, Interfaces)
        for node_id, attrs in g.nodes(data=True):
            data: GraphNodeData = attrs.get("data")
            if not data or data.node_type in {"repository", "package", "file"}:
                continue

            file_id = file_node_id_map.get(data.file_path)
            if not file_id:
                continue

            sym_db = Symbol(
                analysis_run_id=analysis_run_id,
                file_id=file_id,
                name=data.name,
                qualified_name=data.qualified_name,
                symbol_type=data.node_type,
                start_line=data.metadata.get("start_line", 1),
                end_line=data.metadata.get("end_line", 1),
                metadata_json=data.metadata,
            )
            db.add(sym_db)
            await db.flush()
            symbol_node_id_map[node_id] = sym_db.id

        # 3. Persist Graph Edges
        edge_count = 0
        for u, v, attrs in g.edges(data=True):
            source_id = symbol_node_id_map.get(u)
            target_id = symbol_node_id_map.get(v)

            if source_id and target_id:
                edge_db = GraphEdge(
                    analysis_run_id=analysis_run_id,
                    source_symbol_id=source_id,
                    target_symbol_id=target_id,
                    edge_type=attrs.get("edge_type", "imports"),
                    line_number=attrs.get("line_number"),
                    properties=attrs.get("properties"),
                )
                db.add(edge_db)
                edge_count += 1

        await db.commit()
        logger.info(
            "Graph persistence complete: %d files, %d symbols, %d edges saved.",
            len(file_node_id_map),
            len(symbol_node_id_map) - len(file_node_id_map),
            edge_count,
        )


graph_persistence_service = GraphPersistenceService()
