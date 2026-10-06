import fnmatch
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from backend.app.core.logging import logger
from backend.app.graph.builder import GraphNodeData
from backend.app.rules.config import ArchitectureRulesConfig


@dataclass
class DetectedViolation:
    rule_name: str
    severity: str  # error, warning, info
    message: str
    source_file_path: str
    target_file_path: str = ""
    layer_from: str | None = None
    layer_to: str | None = None


class ArchitectureRuleEngine:
    """
    Evaluates configurable architectural boundaries, layer constraints,
    oversized modules, coupling ceilings, and unreferenced code.
    """

    def __init__(self, config: ArchitectureRulesConfig | None = None) -> None:
        self.config = config or ArchitectureRulesConfig.default_clean_architecture()

    def _determine_layer(self, file_path: str) -> str | None:
        """Matches file path against configured layer glob patterns."""
        norm_path = file_path.replace("\\", "/")
        for layer in self.config.layers:
            for pattern in layer.patterns:
                if fnmatch.fnmatch(norm_path, pattern) or fnmatch.fnmatch(f"/{norm_path}", pattern):
                    return layer.name
        return None

    def evaluate_architecture(self, g: nx.MultiDiGraph) -> list[DetectedViolation]:
        logger.info("Evaluating architecture rules: %s...", self.config.name)
        violations: list[DetectedViolation] = []

        # 1. Map all files to layers and collect metrics
        file_layers: dict[str, str | None] = {}
        file_nodes: dict[str, GraphNodeData] = {}

        for _, attrs in g.nodes(data=True):
            data: GraphNodeData = attrs.get("data")
            if data and data.node_type == "file" and data.file_path:
                norm_p = data.file_path.replace("\\", "/")
                file_nodes[norm_p] = data
                file_layers[norm_p] = self._determine_layer(norm_p)

        # 2. Check Layer Boundary Violations
        # Build disallowed transitions lookup: (src_layer, tgt_layer) -> rule
        disallowed_map = {
            (r.source_layer.lower(), r.target_layer.lower()): r
            for r in self.config.rules
            if not r.allowed
        }

        for u, v, d in g.edges(data=True):
            if d.get("edge_type") not in {"imports", "calls", "inherits", "implements"}:
                continue

            u_data: GraphNodeData = g.nodes[u].get("data")
            v_data: GraphNodeData = g.nodes[v].get("data")

            if not u_data or not v_data:
                continue

            u_file = (u_data.file_path or "").replace("\\", "/")
            v_file = (v_data.file_path or "").replace("\\", "/")

            if not u_file or not v_file or u_file == v_file:
                continue

            src_layer = file_layers.get(u_file)
            tgt_layer = file_layers.get(v_file)

            if src_layer and tgt_layer and src_layer != tgt_layer:
                key = (src_layer.lower(), tgt_layer.lower())
                if key in disallowed_map:
                    rule = disallowed_map[key]
                    violations.append(
                        DetectedViolation(
                            rule_name="Layer Boundary Violation",
                            severity=rule.severity,
                            message=f"{rule.description} (File '{u_file}' [{src_layer}] -> '{v_file}' [{tgt_layer}])",
                            source_file_path=u_file,
                            target_file_path=v_file,
                            layer_from=src_layer,
                            layer_to=tgt_layer,
                        )
                    )

        # 3. Check Oversized Modules (LOC Ceiling)
        for fp, data in file_nodes.items():
            if data.loc > self.config.max_file_loc:
                violations.append(
                    DetectedViolation(
                        rule_name="Oversized Module",
                        severity="warning",
                        message=f"Module '{fp}' has {data.loc} lines of code, exceeding threshold of {self.config.max_file_loc} LOC.",
                        source_file_path=fp,
                    )
                )

        # 4. Check Highly Coupled Modules (Excessive Fan-Out)
        for fp, data in file_nodes.items():
            if data.fan_out > self.config.max_efferent_coupling:
                violations.append(
                    DetectedViolation(
                        rule_name="Excessive Coupling",
                        severity="warning",
                        message=f"Module '{fp}' depends on {data.fan_out} other components, exceeding fan-out limit of {self.config.max_efferent_coupling}.",
                        source_file_path=fp,
                    )
                )

        # 5. Check Potentially Dead / Unreferenced Code
        entry_point_names = {"main.py", "app.py", "index.ts", "index.js", "setup.py", "wsgi.py"}
        for fp, data in file_nodes.items():
            p = Path(fp)
            is_test = "test" in fp.lower()
            is_entry = p.name in entry_point_names or "init" in p.stem
            if not is_test and not is_entry:
                if data.fan_in == 0:
                    violations.append(
                        DetectedViolation(
                            rule_name="Potentially Dead Code",
                            severity="info",
                            message=f"Module '{fp}' has zero incoming dependencies and is not recognized as a main entrypoint.",
                            source_file_path=fp,
                        )
                    )

        logger.info("Architecture evaluation complete: %d violation(s) identified.", len(violations))
        return violations


architecture_rule_engine = ArchitectureRuleEngine()
