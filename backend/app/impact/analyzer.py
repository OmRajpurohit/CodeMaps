from collections import deque

import networkx as nx

from backend.app.core.logging import logger
from backend.app.graph.algorithms import graph_algorithms
from backend.app.graph.builder import GraphNodeData
from backend.app.schemas.graph import ImpactAnalysisResponse, ImpactNode


class ImpactAnalyzer:
    """
    Computes upstream change impact (blast radius) for files, classes, or functions.
    Answers: "What could break if this component changes?"
    """

    TEST_PATTERNS = {"test_", "_test.", ".spec.", ".test."}
    API_PATTERNS = {"controller", "api", "route", "endpoint", "views"}

    def analyze_impact(
        self,
        g: nx.MultiDiGraph,
        target_id: str,
        max_depth: int = 8,
    ) -> ImpactAnalysisResponse:
        logger.info("Performing change impact analysis for node %s...", target_id)

        # Ensure node exists
        if target_id not in g:
            # Try fuzzy matching by file path or short name
            matched = None
            for n, d in g.nodes(data=True):
                data: GraphNodeData = d.get("data")
                if data and (
                    data.file_path == target_id
                    or data.name == target_id
                    or data.qualified_name == target_id
                ):
                    matched = n
                    break
            if not matched:
                raise ValueError(f"Node '{target_id}' not found in code graph.")
            target_id = matched

        target_data: GraphNodeData = g.nodes[target_id].get("data")
        target_name = target_data.name if target_data else target_id

        # Extract dependency subgraph and reverse it for upstream traversal
        sub = graph_algorithms.extract_dependency_subgraph(g)
        if target_id not in sub:
            return ImpactAnalysisResponse(
                target_node_id=target_id,
                target_name=target_name,
                impact_score=0.0,
                direct_dependents_count=0,
                transitive_dependents_count=0,
                affected_nodes=[],
                dependency_chain=[],
            )

        transposed = sub.reverse(copy=True)

        visited_depths: dict[str, int] = {}
        paths_to_target: dict[str, list[str]] = {target_id: [target_id]}
        queue: deque[tuple[str, int]] = deque([(target_id, 0)])

        while queue:
            curr, depth = queue.popleft()
            if curr in visited_depths:
                continue

            visited_depths[curr] = depth
            if depth >= max_depth:
                continue

            for upstream_neighbor in transposed.neighbors(curr):
                if upstream_neighbor not in visited_depths:
                    if upstream_neighbor not in paths_to_target:
                        paths_to_target[upstream_neighbor] = [upstream_neighbor] + paths_to_target[curr]
                    queue.append((upstream_neighbor, depth + 1))

        # Remove target node itself from dependents
        visited_depths.pop(target_id, None)

        affected_nodes: list[ImpactNode] = []
        direct_count = 0
        raw_score = 0.0

        for dep_id, depth in visited_depths.items():
            node_data: GraphNodeData = g.nodes[dep_id].get("data")
            name = node_data.name if node_data else dep_id.split(":")[-1]
            node_type = node_data.node_type if node_data else "unknown"
            file_path = node_data.file_path or ""
            is_direct = depth == 1

            if is_direct:
                direct_count += 1

            # Check if affected node is a test file
            is_test = any(pat in file_path.lower() for pat in self.TEST_PATTERNS)
            is_api = any(pat in file_path.lower() for pat in self.API_PATTERNS)

            # Weight calculation
            weight = 10.0 / depth
            if is_api:
                weight += 12.0 / depth  # APIs/controllers are critical entry points
            if is_test:
                weight += 4.0 / depth

            raw_score += weight

            affected_nodes.append(
                ImpactNode(
                    node_id=dep_id,
                    name=name,
                    node_type=node_type,
                    depth=depth,
                    impact_weight=round(weight, 2),
                    is_direct=is_direct,
                    is_test_file=is_test,
                )
            )

        # Sort affected nodes by depth, then impact weight
        affected_nodes.sort(key=lambda n: (n.depth, -n.impact_weight))

        # Sample dependency chains (e.g. database.py <- repository.py <- service.py <- controller.py)
        sample_chains: list[list[str]] = []
        deepest_nodes = sorted(affected_nodes, key=lambda n: n.depth, reverse=True)[:5]
        for dn in deepest_nodes:
            path = paths_to_target.get(dn.node_id, [])
            clean_path = [n.split(":")[-1] for n in path]
            sample_chains.append(clean_path)

        # Normalized impact score (0.0 to 100.0)
        normalized_impact_score = round(min(100.0, raw_score), 2)
        transitive_count = max(0, len(affected_nodes) - direct_count)

        logger.info(
            "Impact analysis complete for %s: %d direct, %d transitive dependents (impact score: %.1f)",
            target_name,
            direct_count,
            transitive_count,
            normalized_impact_score,
        )

        return ImpactAnalysisResponse(
            target_node_id=target_id,
            target_name=target_name,
            impact_score=normalized_impact_score,
            direct_dependents_count=direct_count,
            transitive_dependents_count=transitive_count,
            affected_nodes=affected_nodes,
            dependency_chain=sample_chains,
        )


impact_analyzer = ImpactAnalyzer()
