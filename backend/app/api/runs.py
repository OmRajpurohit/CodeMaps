import networkx as nx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.graph.algorithms import graph_algorithms
from backend.app.impact.analyzer import impact_analyzer
from backend.app.models import (
    AnalysisRun,
    FileNode,
    GitCommit,
    GitFileChurn,
    GraphEdge,
    Hotspot,
    Repository,
    Symbol,
    Violation,
)
from backend.app.schemas import (
    CyclesResponse,
    DependencyGraphResponse,
    GraphEdgeSchema,
    GraphNode,
    HotspotResponse,
    HotspotsListResponse,
    ImpactAnalysisResponse,
    RepositoryOverviewResponse,
    ViolationResponse,
    ViolationsListResponse,
)

router = APIRouter()


@router.get("/{run_id}/overview", response_model=RepositoryOverviewResponse, summary="Get run overview & health")
async def get_run_overview(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> RepositoryOverviewResponse:
    stmt = select(AnalysisRun).where(AnalysisRun.id == run_id)
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    repo_stmt = select(Repository).where(Repository.id == run.repository_id)
    repo_res = await db.execute(repo_stmt)
    repo = repo_res.scalar_one_or_none()

    stats = run.summary_stats or {}
    return RepositoryOverviewResponse(
        repository_id=run.repository_id,
        name=repo.name if repo else "unknown",
        url=repo.url if repo else "",
        commit_sha=run.commit_sha,
        status=run.status,
        total_files=stats.get("total_files", 0),
        total_symbols=stats.get("total_symbols", 0),
        total_loc=stats.get("total_loc", 0),
        primary_language=stats.get("primary_language"),
        languages_breakdown=stats.get("languages_breakdown", {}),
        health_score=stats.get("health_score", 100.0),
        total_cycles=stats.get("total_cycles", 0),
        total_violations=stats.get("total_violations", 0),
        total_hotspots=stats.get("total_hotspots", 0),
    )


@router.get("/{run_id}/graph", response_model=DependencyGraphResponse, summary="Get dependency graph")
async def get_run_graph(
    run_id: str,
    node_type: str | None = Query(None, description="Filter by node type: file, class, function, method"),
    limit: int = Query(500, le=2000),
    db: AsyncSession = Depends(get_db),
) -> DependencyGraphResponse:
    # 1. Fetch FileNodes
    files_stmt = select(FileNode).where(FileNode.analysis_run_id == run_id)
    files_res = await db.execute(files_stmt)
    file_records = list(files_res.scalars().all())

    # 2. Fetch Symbols
    sym_stmt = select(Symbol).where(Symbol.analysis_run_id == run_id)
    if node_type and node_type != "file":
        sym_stmt = sym_stmt.where(Symbol.symbol_type == node_type)
    sym_res = await db.execute(sym_stmt)
    symbol_records = list(sym_res.scalars().all())

    nodes: list[GraphNode] = []
    symbol_id_to_node_id: dict[str, str] = {}

    # Add File Nodes if matching filter
    if not node_type or node_type == "file":
        for fn in file_records:
            node_id = f"file:{fn.path}"
            symbol_id_to_node_id[fn.id] = node_id
            nodes.append(
                GraphNode(
                    id=node_id,
                    name=fn.path.split("/")[-1],
                    qualified_name=fn.path,
                    node_type="file",
                    file_path=fn.path,
                    loc=fn.loc,
                    complexity=fn.cyclomatic_complexity,
                    fan_in=fn.afferent_coupling,
                    fan_out=fn.efferent_coupling,
                    instability=fn.instability,
                )
            )

    # Add Symbols
    for sym in symbol_records:
        node_id = f"{sym.symbol_type}:{sym.qualified_name}"
        symbol_id_to_node_id[sym.id] = node_id
        nodes.append(
            GraphNode(
                id=node_id,
                name=sym.name,
                qualified_name=sym.qualified_name,
                node_type=sym.symbol_type,
                metadata=sym.metadata_json or {},
            )
        )

    # 3. Fetch Edges
    edges_stmt = select(GraphEdge).where(GraphEdge.analysis_run_id == run_id).limit(limit)
    edges_res = await db.execute(edges_stmt)
    edge_records = list(edges_res.scalars().all())

    edges: list[GraphEdgeSchema] = []
    for e in edge_records:
        src = symbol_id_to_node_id.get(e.source_symbol_id)
        tgt = symbol_id_to_node_id.get(e.target_symbol_id)
        if src and tgt:
            edges.append(
                GraphEdgeSchema(
                    id=e.id,
                    source=src,
                    target=tgt,
                    edge_type=e.edge_type,
                    line_number=e.line_number,
                    properties=e.properties or {},
                )
            )

    return DependencyGraphResponse(
        nodes=nodes[:limit],
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
    )


@router.get("/{run_id}/cycles", response_model=CyclesResponse, summary="Get detected cycles and SCCs")
async def get_run_cycles(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> CyclesResponse:
    # Reconstruct dependency graph from edges to compute cycles
    edges_stmt = select(GraphEdge).where(GraphEdge.analysis_run_id == run_id)
    edges_res = await db.execute(edges_stmt)
    edge_records = list(edges_res.scalars().all())

    # Map symbol IDs to readable names
    files_stmt = select(FileNode).where(FileNode.analysis_run_id == run_id)
    files_res = await db.execute(files_stmt)
    id_map = {f.id: f"file:{f.path}" for f in files_res.scalars().all()}

    syms_stmt = select(Symbol).where(Symbol.analysis_run_id == run_id)
    syms_res = await db.execute(syms_stmt)
    id_map.update({s.id: f"{s.symbol_type}:{s.qualified_name}" for s in syms_res.scalars().all()})

    g = nx.MultiDiGraph()
    for e in edge_records:
        src = id_map.get(e.source_symbol_id)
        tgt = id_map.get(e.target_symbol_id)
        if src and tgt:
            g.add_edge(src, tgt, edge_type=e.edge_type)

    cycles = graph_algorithms.detect_cycles(g)
    sccs = graph_algorithms.detect_scc(g)

    return CyclesResponse(
        total_cycles=len(cycles),
        cycles=cycles,
        scc_clusters=sccs,
    )


@router.get("/{run_id}/impact", response_model=ImpactAnalysisResponse, summary="Calculate blast radius")
async def get_run_impact(
    run_id: str,
    target: str = Query(..., description="Target node ID, symbol qualified name, or relative file path"),
    db: AsyncSession = Depends(get_db),
) -> ImpactAnalysisResponse:
    # Build in-memory graph from run data
    edges_stmt = select(GraphEdge).where(GraphEdge.analysis_run_id == run_id)
    edges_res = await db.execute(edges_stmt)
    edge_records = list(edges_res.scalars().all())

    files_stmt = select(FileNode).where(FileNode.analysis_run_id == run_id)
    files_res = await db.execute(files_stmt)
    file_map = {f.id: f for f in files_res.scalars().all()}

    syms_stmt = select(Symbol).where(Symbol.analysis_run_id == run_id)
    syms_res = await db.execute(syms_stmt)
    sym_map = {s.id: s for s in syms_res.scalars().all()}

    g = nx.MultiDiGraph()
    # Add files
    for fid, f in file_map.items():
        node_id = f"file:{f.path}"
        g.add_node(
            node_id,
            data=GraphNode(
                id=node_id,
                name=f.path.split("/")[-1],
                qualified_name=f.path,
                node_type="file",
                file_path=f.path,
            ),
        )

    # Add symbols
    for sid, s in sym_map.items():
        node_id = f"{s.symbol_type}:{s.qualified_name}"
        f = file_map.get(s.file_id)
        g.add_node(
            node_id,
            data=GraphNode(
                id=node_id,
                name=s.name,
                qualified_name=s.qualified_name,
                node_type=s.symbol_type,
                file_path=f.path if f else None,
            ),
        )

    # Add edges
    id_to_name = {f.id: f"file:{f.path}" for f in file_map.values()}
    id_to_name.update({s.id: f"{s.symbol_type}:{s.qualified_name}" for s in sym_map.values()})

    for e in edge_records:
        src = id_to_name.get(e.source_symbol_id)
        tgt = id_to_name.get(e.target_symbol_id)
        if src and tgt:
            g.add_edge(src, tgt, edge_type=e.edge_type)

    return impact_analyzer.analyze_impact(g, target)


@router.get("/{run_id}/hotspots", response_model=HotspotsListResponse, summary="Get ranked hotspots")
async def get_run_hotspots(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> HotspotsListResponse:
    stmt = (
        select(Hotspot)
        .where(Hotspot.analysis_run_id == run_id)
        .order_by(Hotspot.score.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    hotspots = list(result.scalars().all())
    return HotspotsListResponse(
        total_hotspots=len(hotspots),
        hotspots=[HotspotResponse.model_validate(h) for h in hotspots],
    )


@router.get("/{run_id}/violations", response_model=ViolationsListResponse, summary="Get architecture violations")
async def get_run_violations(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> ViolationsListResponse:
    stmt = (
        select(Violation)
        .where(Violation.analysis_run_id == run_id)
        .order_by(Violation.created_at.asc())
    )
    result = await db.execute(stmt)
    violations = list(result.scalars().all())
    return ViolationsListResponse(
        total_violations=len(violations),
        violations=[ViolationResponse.model_validate(v) for v in violations],
    )


@router.get("/{run_id}/commits", summary="Get Git commit history and file churn")
async def get_run_commits(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    commits_stmt = (
        select(GitCommit)
        .where(GitCommit.analysis_run_id == run_id)
        .order_by(GitCommit.authored_at.desc())
        .limit(50)
    )
    commits_res = await db.execute(commits_stmt)

    churn_stmt = (
        select(GitFileChurn)
        .where(GitFileChurn.analysis_run_id == run_id)
        .order_by(GitFileChurn.commit_count.desc())
        .limit(50)
    )
    churn_res = await db.execute(churn_stmt)

    return {
        "commits": list(commits_res.scalars().all()),
        "file_churns": list(churn_res.scalars().all()),
    }
