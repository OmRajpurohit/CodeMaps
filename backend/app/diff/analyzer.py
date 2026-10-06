from dataclasses import dataclass, field

import networkx as nx

from backend.app.core.logging import logger
from backend.app.graph.algorithms import graph_algorithms


@dataclass
class EdgeDiffItem:
    source: str
    target: str
    edge_type: str


@dataclass
class CouplingDelta:
    file_path: str
    old_fan_in: int
    new_fan_in: int
    old_fan_out: int
    new_fan_out: int


@dataclass
class ArchitectureDiffResult:
    base_commit: str
    target_commit: str
    dependencies_added: list[EdgeDiffItem] = field(default_factory=list)
    dependencies_removed: list[EdgeDiffItem] = field(default_factory=list)
    new_cycles_introduced: list[list[str]] = field(default_factory=list)
    coupling_deltas: list[CouplingDelta] = field(default_factory=list)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    risk_score: float = 0.0
    risk_summary: list[str] = field(default_factory=list)


class ArchitectureDiffAnalyzer:
    """
    Compares two graph snapshots corresponding to two Git revisions.
    Identifies structural regressions: new cycles, added dependencies, increased coupling.
    """

    def diff_graphs(
        self,
        g_base: nx.MultiDiGraph,
        g_target: nx.MultiDiGraph,
        base_commit: str = "HEAD~1",
        target_commit: str = "HEAD",
    ) -> ArchitectureDiffResult:
        logger.info("Computing architecture diff between %s and %s...", base_commit, target_commit)

        # 1. Compare Dependency Edges
        def get_edges_set(g: nx.MultiDiGraph) -> set[tuple[str, str, str]]:
            s = set()
            for u, v, d in g.edges(data=True):
                etype = d.get("edge_type", "")
                if etype in {"imports", "calls", "inherits", "implements"}:
                    s.add((u, v, etype))
            return s

        base_edges = get_edges_set(g_base)
        target_edges = get_edges_set(g_target)

        added = target_edges - base_edges
        removed = base_edges - target_edges

        added_list = [EdgeDiffItem(source=u, target=v, edge_type=t) for u, v, t in added]
        removed_list = [EdgeDiffItem(source=u, target=v, edge_type=t) for u, v, t in removed]

        # 2. Cycle Regression Detection
        base_cycles = {tuple(c.nodes) for c in graph_algorithms.detect_cycles(g_base)}
        target_cycles = {tuple(c.nodes) for c in graph_algorithms.detect_cycles(g_target)}

        new_cycles = [list(c) for c in (target_cycles - base_cycles)]

        # 3. Coupling Changes (Fan-in / Fan-out)
        base_metrics = graph_algorithms.compute_metrics(g_base)
        target_metrics = graph_algorithms.compute_metrics(g_target)

        coupling_deltas: list[CouplingDelta] = []
        all_nodes = set(base_metrics.fan_in.keys()) | set(target_metrics.fan_in.keys())

        for node in all_nodes:
            if not node.startswith("file:"):
                continue
            b_in = base_metrics.fan_in.get(node, 0)
            t_in = target_metrics.fan_in.get(node, 0)
            b_out = base_metrics.fan_out.get(node, 0)
            t_out = target_metrics.fan_out.get(node, 0)

            if b_in != t_in or b_out != t_out:
                coupling_deltas.append(
                    CouplingDelta(
                        file_path=node.replace("file:", ""),
                        old_fan_in=b_in,
                        new_fan_in=t_in,
                        old_fan_out=b_out,
                        new_fan_out=t_out,
                    )
                )

        # 4. Architectural Risk Scoring
        risk_score = 0.0
        risk_summary: list[str] = []

        if new_cycles:
            risk_score += 45.0 * len(new_cycles)
            risk_summary.append(f"Introduced {len(new_cycles)} new circular dependency loop(s).")

        significant_fan_out_increases = [
            cd for cd in coupling_deltas if cd.new_fan_out > cd.old_fan_out + 2
        ]
        if significant_fan_out_increases:
            risk_score += 15.0 * len(significant_fan_out_increases)
            risk_summary.append(
                f"{len(significant_fan_out_increases)} file(s) exhibited significant increase in efferent coupling (fan-out)."
            )

        if len(added_list) > 20:
            risk_score += 10.0
            risk_summary.append(f"High dependency churn: {len(added_list)} new dependencies introduced.")

        if not risk_summary:
            risk_summary.append("No significant architectural regressions detected.")

        risk_score = min(100.0, risk_score)
        if risk_score >= 60.0:
            risk_level = "CRITICAL"
        elif risk_score >= 35.0:
            risk_level = "HIGH"
        elif risk_score >= 15.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        logger.info(
            "Architecture diff complete: %d added, %d removed, %d new cycles (Risk: %s, Score: %.1f)",
            len(added_list),
            len(removed_list),
            len(new_cycles),
            risk_level,
            risk_score,
        )

        return ArchitectureDiffResult(
            base_commit=base_commit,
            target_commit=target_commit,
            dependencies_added=added_list,
            dependencies_removed=removed_list,
            new_cycles_introduced=new_cycles,
            coupling_deltas=coupling_deltas,
            risk_level=risk_level,
            risk_score=risk_score,
            risk_summary=risk_summary,
        )


architecture_diff_analyzer = ArchitectureDiffAnalyzer()
