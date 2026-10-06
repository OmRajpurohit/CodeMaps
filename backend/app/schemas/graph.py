from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    name: str
    qualified_name: str
    node_type: str  # package, file, class, function, method
    file_path: str | None = None
    loc: int | None = None
    complexity: float | None = None
    fan_in: int = 0
    fan_out: int = 0
    instability: float = 0.0
    degree_centrality: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeSchema(BaseModel):
    id: str
    source: str
    target: str
    edge_type: str  # imports, calls, inherits, implements, contains
    line_number: int | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class DependencyGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdgeSchema]
    total_nodes: int
    total_edges: int


class CyclePath(BaseModel):
    length: int
    nodes: list[str]  # e.g. ["module_a.py", "module_b.py", "module_a.py"]
    description: str


class StronglyConnectedComponent(BaseModel):
    size: int
    nodes: list[str]


class CyclesResponse(BaseModel):
    total_cycles: int
    cycles: list[CyclePath]
    scc_clusters: list[StronglyConnectedComponent]


class ImpactNode(BaseModel):
    node_id: str
    name: str
    node_type: str
    depth: int
    impact_weight: float
    is_direct: bool
    is_test_file: bool = False


class ImpactAnalysisResponse(BaseModel):
    target_node_id: str
    target_name: str
    impact_score: float  # Normalized blast radius score 0.0 - 100.0
    direct_dependents_count: int
    transitive_dependents_count: int
    affected_nodes: list[ImpactNode]
    dependency_chain: list[list[str]]  # Sample shortest paths to critical dependents
