from collections import deque
from dataclasses import dataclass, field

import networkx as nx

from backend.app.schemas.graph import CyclePath, StronglyConnectedComponent


@dataclass
class GraphMetricsResult:
    fan_in: dict[str, int] = field(default_factory=dict)
    fan_out: dict[str, int] = field(default_factory=dict)
    instability: dict[str, float] = field(default_factory=dict)
    degree_centrality: dict[str, float] = field(default_factory=dict)
    dependency_depth: dict[str, int] = field(default_factory=dict)


class GraphAlgorithms:
    """
    Graph algorithms for architecture analysis:
    - Tarjan's Strongly Connected Components (SCC)
    - Elementary cycle detection
    - BFS/DFS reverse dependency traversal
    - Coupling, instability, centrality, and depth metrics
    """

    DEPENDENCY_EDGE_TYPES = {"imports", "calls", "inherits", "implements"}

    def extract_dependency_subgraph(
        self,
        g: nx.MultiDiGraph,
        node_types: set[str] | None = None,
    ) -> nx.DiGraph:
        """
        Creates a simple directed graph containing only architectural dependency edges
        (imports, calls, inherits, implements), excluding containment hierarchy edges.
        """
        sub = nx.DiGraph()

        for u, v, data in g.edges(data=True):
            if data.get("edge_type") in self.DEPENDENCY_EDGE_TYPES:
                u_data = g.nodes[u].get("data")
                v_data = g.nodes[v].get("data")
                u_type = getattr(u_data, "node_type", None) if u_data else None
                v_type = getattr(v_data, "node_type", None) if v_data else None

                if node_types:
                    if u_type not in node_types or v_type not in node_types:
                        continue

                sub.add_edge(u, v, **data)

        # Also add isolated nodes if node_types specified
        if node_types:
            for n, d in g.nodes(data=True):
                data_obj = d.get("data")
                if data_obj and data_obj.node_type in node_types:
                    sub.add_node(n, **d)

        return sub

    def detect_scc(self, g: nx.MultiDiGraph, node_types: set[str] | None = None) -> list[StronglyConnectedComponent]:
        """
        Computes Strongly Connected Components (SCC) using Tarjan's algorithm.
        Returns components with size > 1 (i.e. circular dependency clusters).
        """
        sub = self.extract_dependency_subgraph(g, node_types=node_types)
        sccs = list(nx.strongly_connected_components(sub))

        clusters: list[StronglyConnectedComponent] = []
        for scc in sccs:
            if len(scc) > 1:
                clusters.append(
                    StronglyConnectedComponent(
                        size=len(scc),
                        nodes=sorted(list(scc)),
                    )
                )

        return sorted(clusters, key=lambda c: c.size, reverse=True)

    def detect_cycles(
        self,
        g: nx.MultiDiGraph,
        node_types: set[str] | None = None,
        max_cycles: int = 50,
    ) -> list[CyclePath]:
        """
        Detects elementary directed cycles in the dependency graph.
        Returns formatted cycle paths.
        """
        sub = self.extract_dependency_subgraph(g, node_types=node_types)
        cycles: list[CyclePath] = []

        try:
            raw_cycles = list(nx.simple_cycles(sub))
            # Sort cycles by length (shortest cycles first)
            raw_cycles.sort(key=len)

            for c in raw_cycles[:max_cycles]:
                cycle_nodes = c + [c[0]]  # Close the cycle
                desc = " -> ".join([n.split(":")[-1] for n in cycle_nodes])
                cycles.append(
                    CyclePath(
                        length=len(c),
                        nodes=cycle_nodes,
                        description=desc,
                    )
                )
        except Exception:
            pass

        return cycles

    def compute_metrics(self, g: nx.MultiDiGraph) -> GraphMetricsResult:
        """
        Calculates fan-in, fan-out, Martin's instability metric,
        degree centrality, and dependency depth for all nodes in the dependency graph.
        """
        sub = self.extract_dependency_subgraph(g)
        num_nodes = sub.number_of_nodes()

        fan_in: dict[str, int] = {}
        fan_out: dict[str, int] = {}
        instability: dict[str, float] = {}
        degree_centrality: dict[str, float] = {}
        dependency_depth: dict[str, int] = {}

        if num_nodes == 0:
            return GraphMetricsResult()

        raw_centrality = nx.degree_centrality(sub)

        for node in sub.nodes():
            in_deg = sub.in_degree(node)
            out_deg = sub.out_degree(node)
            total_deg = in_deg + out_deg

            fan_in[node] = in_deg
            fan_out[node] = out_deg
            instability[node] = round(out_deg / total_deg, 3) if total_deg > 0 else 0.0
            degree_centrality[node] = round(raw_centrality.get(node, 0.0), 4)

        # Calculate dependency depth in DAG or condensation graph
        try:
            if nx.is_directed_acyclic_graph(sub):
                lengths = dict(nx.all_pairs_shortest_path_length(sub))
                for node in sub.nodes():
                    depths = [lengths[src][node] for src in lengths if node in lengths[src]]
                    dependency_depth[node] = max(depths) if depths else 0
            else:
                # Condensation DAG
                cond = nx.condensation(sub)
                lengths = dict(nx.all_pairs_shortest_path_length(cond))
                mapping = cond.graph["mapping"]
                for node in sub.nodes():
                    scc_id = mapping.get(node)
                    depths = [lengths[src][scc_id] for src in lengths if scc_id in lengths[src]]
                    dependency_depth[node] = max(depths) if depths else 0
        except Exception:
            for node in sub.nodes():
                dependency_depth[node] = 0

        # Update node data in graph
        for node in g.nodes():
            data_obj = g.nodes[node].get("data")
            if data_obj:
                data_obj.fan_in = fan_in.get(node, 0)
                data_obj.fan_out = fan_out.get(node, 0)
                data_obj.instability = instability.get(node, 0.0)
                data_obj.degree_centrality = degree_centrality.get(node, 0.0)

        return GraphMetricsResult(
            fan_in=fan_in,
            fan_out=fan_out,
            instability=instability,
            degree_centrality=degree_centrality,
            dependency_depth=dependency_depth,
        )

    def reverse_bfs_traversal(
        self,
        g: nx.MultiDiGraph,
        start_node_id: str,
        max_depth: int = 10,
    ) -> dict[str, int]:
        """
        Performs BFS on the transposed dependency graph $G^T$.
        Traverses upstream to find all components that depend on `start_node_id` (blast radius).
        Returns mapping of dependent_node_id -> distance (depth).
        """
        sub = self.extract_dependency_subgraph(g)
        if start_node_id not in sub:
            return {}

        transposed = sub.reverse(copy=True)
        visited_depths: dict[str, int] = {}
        queue: deque[tuple[str, int]] = deque([(start_node_id, 0)])

        while queue:
            curr_node, depth = queue.popleft()
            if curr_node in visited_depths:
                continue

            visited_depths[curr_node] = depth
            if depth >= max_depth:
                continue

            for neighbor in transposed.neighbors(curr_node):
                if neighbor not in visited_depths:
                    queue.append((neighbor, depth + 1))

        # Remove start node itself from dependents
        visited_depths.pop(start_node_id, None)
        return visited_depths

    def find_shortest_paths(
        self,
        g: nx.MultiDiGraph,
        source: str,
        target: str,
    ) -> list[str]:
        """Finds shortest dependency path between source and target."""
        sub = self.extract_dependency_subgraph(g)
        try:
            return nx.shortest_path(sub, source=source, target=target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []


graph_algorithms = GraphAlgorithms()
