from dataclasses import dataclass

import networkx as nx

from backend.app.core.logging import logger
from backend.app.git.analyzer import FileChurnMetric
from backend.app.graph.builder import GraphNodeData


@dataclass
class ScoredHotspot:
    file_path: str
    score: float
    churn_score: float
    centrality_score: float
    complexity_score: float
    rationale: str


class HotspotEngine:
    """
    Combines static graph centrality and AST complexity metrics with
    dynamic Git churn to calculate transparent, actionable hotspot scores.
    """

    def calculate_hotspots(
        self,
        g: nx.MultiDiGraph,
        file_churns: dict[str, FileChurnMetric],
    ) -> list[ScoredHotspot]:
        logger.info("Computing architectural hotspots...")

        # 1. Gather all file nodes from graph
        file_nodes: dict[str, GraphNodeData] = {}
        for _, attrs in g.nodes(data=True):
            data: GraphNodeData = attrs.get("data")
            if data and data.node_type == "file" and data.file_path:
                norm_p = data.file_path.replace("\\", "/")
                file_nodes[norm_p] = data

        if not file_nodes:
            return []

        # 2. Extract raw metrics
        raw_churn: dict[str, float] = {}
        raw_centrality: dict[str, float] = {}
        raw_complexity: dict[str, float] = {}

        for fp, node in file_nodes.items():
            churn_info = file_churns.get(fp)
            # Churn metric combines commit count and total line churn
            c_val = (
                (churn_info.commit_count * 10 + churn_info.total_churn)
                if churn_info
                else 0.0
            )
            raw_churn[fp] = float(c_val)

            # Centrality combines fan-in (dependents) and degree centrality
            fan_in = node.fan_in
            deg_cent = node.degree_centrality
            raw_centrality[fp] = float(fan_in * 2.0 + deg_cent * 10.0)

            raw_complexity[fp] = float(node.cyclomatic_complexity)

        # 3. Normalization (min-max scaling 0.0 - 1.0)
        def normalize_map(m: dict[str, float]) -> dict[str, float]:
            vals = list(m.values())
            min_v = min(vals) if vals else 0.0
            max_v = max(vals) if vals else 0.0
            rng = max_v - min_v
            if rng <= 0.0001:
                return {k: 0.5 if max_v > 0 else 0.0 for k in m}
            return {k: (v - min_v) / rng for k, v in m.items()}

        norm_churn = normalize_map(raw_churn)
        norm_centrality = normalize_map(raw_centrality)

        # 4. Score calculation & Rationale synthesis
        hotspots: list[ScoredHotspot] = []

        for fp in file_nodes:
            c_score = norm_churn[fp]
            cent_score = norm_centrality[fp]
            comp = raw_complexity[fp]

            # Complexity weight factor (1.0 to 2.5)
            comp_weight = min(2.5, 1.0 + (comp - 1.0) * 0.05)

            # Unified Hotspot Score (0 - 100)
            base_score = 0.55 * c_score + 0.45 * cent_score
            total_score = round(min(100.0, base_score * comp_weight * 100.0), 2)

            # Synthesize transparent, human-readable rationale
            node = file_nodes[fp]
            churn_info = file_churns.get(fp)
            commits = churn_info.commit_count if churn_info else 0
            churn_lines = churn_info.total_churn if churn_info else 0

            reasons: list[str] = []
            if commits > 0:
                reasons.append(f"{commits} commits ({churn_lines} lines churned)")
            else:
                reasons.append("stable history")

            if node.fan_in > 0:
                reasons.append(f"{node.fan_in} dependent modules (fan-in)")

            if comp > 5.0:
                reasons.append(f"elevated cyclomatic complexity ({comp:.1f})")

            rationale = "High Risk: " + ", ".join(reasons) + "."

            hotspots.append(
                ScoredHotspot(
                    file_path=fp,
                    score=total_score,
                    churn_score=round(c_score * 100.0, 2),
                    centrality_score=round(cent_score * 100.0, 2),
                    complexity_score=round(comp, 2),
                    rationale=rationale,
                )
            )

        # Sort descending by risk score
        hotspots.sort(key=lambda h: h.score, reverse=True)
        logger.info("Computed %d hotspots. Top hotspot: %s (score: %.1f)", len(hotspots), hotspots[0].file_path if hotspots else "None", hotspots[0].score if hotspots else 0)

        return hotspots


hotspot_engine = HotspotEngine()
