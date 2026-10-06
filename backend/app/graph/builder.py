from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

from backend.app.analyzers.base import FileAnalysisResult
from backend.app.core.logging import logger


@dataclass
class GraphNodeData:
    id: str
    name: str
    qualified_name: str
    node_type: str  # repository, package, file, class, function, method, interface
    file_path: str | None = None
    loc: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    cyclomatic_complexity: float = 1.0
    fan_in: int = 0
    fan_out: int = 0
    instability: float = 0.0
    degree_centrality: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdgeData:
    id: str
    source: str
    target: str
    edge_type: str  # contains, imports, calls, inherits, implements
    line_number: int | None = None
    properties: dict[str, Any] = field(default_factory=dict)


class CodeGraphBuilder:
    """
    Constructs a unified, multi-layered directed code graph from AST analysis results.
    Connects repositories, packages, files, classes, methods, and functions.
    """

    def build_graph(
        self,
        repo_name: str,
        analysis_results: list[FileAnalysisResult],
    ) -> nx.MultiDiGraph:
        g = nx.MultiDiGraph()

        # Index maps for symbol and file resolution
        file_node_map: dict[str, str] = {}  # rel_path -> node_id
        module_to_file_map: dict[str, str] = {}  # module dotted/slash name -> rel_path
        symbol_qname_map: dict[str, str] = {}  # qualified_name -> node_id
        symbol_short_map: dict[str, list[str]] = {}  # short name -> list of node_ids

        # 1. Add Repository Root Node
        repo_node_id = f"repo:{repo_name}"
        g.add_node(
            repo_node_id,
            data=GraphNodeData(
                id=repo_node_id,
                name=repo_name,
                qualified_name=repo_name,
                node_type="repository",
            ),
        )

        # 2. Add Packages and Files
        known_packages: set[str] = set()

        for res in analysis_results:
            rel_path = res.file_path.replace("\\", "/")
            file_node_id = f"file:{rel_path}"
            file_node_map[rel_path] = file_node_id

            # Map various module representations to rel_path
            p = Path(rel_path)
            dotted_no_ext = ".".join(list(p.parts[:-1]) + [p.stem])
            slash_no_ext = "/".join(list(p.parts[:-1]) + [p.stem])
            module_to_file_map[dotted_no_ext] = rel_path
            module_to_file_map[slash_no_ext] = rel_path
            module_to_file_map[p.stem] = rel_path

            # Hierarchical package containment
            parent_dir = str(p.parent).replace("\\", "/")
            if parent_dir and parent_dir != ".":
                # Ensure all ancestors exist
                parts = parent_dir.split("/")
                current_pkg = ""
                for part in parts:
                    prev_pkg = current_pkg
                    current_pkg = f"{current_pkg}/{part}" if current_pkg else part
                    pkg_node_id = f"package:{current_pkg}"
                    if pkg_node_id not in known_packages:
                        known_packages.add(pkg_node_id)
                        g.add_node(
                            pkg_node_id,
                            data=GraphNodeData(
                                id=pkg_node_id,
                                name=part,
                                qualified_name=current_pkg,
                                node_type="package",
                            ),
                        )
                        # Link parent package or repo root
                        parent_id = f"package:{prev_pkg}" if prev_pkg else repo_node_id
                        g.add_edge(parent_id, pkg_node_id, edge_type="contains")

                file_parent_id = f"package:{parent_dir}"
            else:
                file_parent_id = repo_node_id

            # Add File Node
            g.add_node(
                file_node_id,
                data=GraphNodeData(
                    id=file_node_id,
                    name=p.name,
                    qualified_name=rel_path,
                    node_type="file",
                    file_path=rel_path,
                    loc=res.loc,
                    blank_lines=res.blank_lines,
                    comment_lines=res.comment_lines,
                    cyclomatic_complexity=res.cyclomatic_complexity,
                    metadata={"language": res.language},
                ),
            )
            # Containment: package/repo -> file
            g.add_edge(file_parent_id, file_node_id, edge_type="contains")

            # 3. Add Symbols (Classes, Functions, Methods, Interfaces)
            for sym in res.symbols:
                if sym.symbol_type == "module":
                    continue  # Module represented by file node

                sym_node_id = f"{sym.symbol_type}:{sym.qualified_name}"
                symbol_qname_map[sym.qualified_name] = sym_node_id
                symbol_short_map.setdefault(sym.name, []).append(sym_node_id)

                g.add_node(
                    sym_node_id,
                    data=GraphNodeData(
                        id=sym_node_id,
                        name=sym.name,
                        qualified_name=sym.qualified_name,
                        node_type=sym.symbol_type,
                        file_path=rel_path,
                        metadata={
                            "start_line": sym.start_line,
                            "end_line": sym.end_line,
                            **sym.metadata,
                        },
                    ),
                )

                # Link containment: file or parent class -> symbol
                parent_class = sym.metadata.get("parent_class")
                if parent_class:
                    parent_class_qname = f"class:{res.symbols[0].qualified_name}.{parent_class}"
                    if parent_class_qname in g:
                        g.add_edge(parent_class_qname, sym_node_id, edge_type="contains")
                    else:
                        g.add_edge(file_node_id, sym_node_id, edge_type="contains")
                else:
                    g.add_edge(file_node_id, sym_node_id, edge_type="contains")

        # 4. Resolve and Add Edges (Imports, Inherits, Implements, Calls)
        for res in analysis_results:
            rel_path = res.file_path.replace("\\", "/")
            src_file_node_id = file_node_map[rel_path]

            for edge in res.edges:
                line_no = edge.line_number
                target_str = edge.target.strip()

                if edge.edge_type == "imports":
                    # Resolve import target to internal file node if possible
                    resolved_file = self._resolve_import_target(
                        rel_path, target_str, module_to_file_map, file_node_map
                    )
                    if resolved_file and resolved_file != src_file_node_id:
                        g.add_edge(
                            src_file_node_id,
                            resolved_file,
                            edge_type="imports",
                            line_number=line_no,
                        )

                elif edge.edge_type == "inherits":
                    src_sym_id = symbol_qname_map.get(edge.source) or f"class:{edge.source}"
                    target_sym_id = self._resolve_symbol(edge.target, symbol_qname_map, symbol_short_map)
                    if target_sym_id and src_sym_id in g and target_sym_id in g:
                        g.add_edge(
                            src_sym_id,
                            target_sym_id,
                            edge_type="inherits",
                            line_number=line_no,
                        )
                        # Also induce file-level dependency
                        src_f = g.nodes[src_sym_id]["data"].file_path
                        tgt_f = g.nodes[target_sym_id]["data"].file_path
                        if src_f and tgt_f and src_f != tgt_f:
                            g.add_edge(f"file:{src_f}", f"file:{tgt_f}", edge_type="inherits")

                elif edge.edge_type == "implements":
                    src_sym_id = symbol_qname_map.get(edge.source) or f"class:{edge.source}"
                    target_sym_id = self._resolve_symbol(edge.target, symbol_qname_map, symbol_short_map)
                    if target_sym_id and src_sym_id in g and target_sym_id in g:
                        g.add_edge(
                            src_sym_id,
                            target_sym_id,
                            edge_type="implements",
                            line_number=line_no,
                        )

                elif edge.edge_type == "calls":
                    src_sym_id = symbol_qname_map.get(edge.source) or f"func:{edge.source}"
                    # Match call targets like UserService.find or find
                    call_name = edge.target.split(".")[-1]
                    target_sym_id = self._resolve_symbol(call_name, symbol_qname_map, symbol_short_map)
                    if target_sym_id and src_sym_id in g and target_sym_id in g:
                        g.add_edge(
                            src_sym_id,
                            target_sym_id,
                            edge_type="calls",
                            line_number=line_no,
                        )
                        # Induce file-level call edge
                        src_f = g.nodes[src_sym_id]["data"].file_path
                        tgt_f = g.nodes[target_sym_id]["data"].file_path
                        if src_f and tgt_f and src_f != tgt_f:
                            g.add_edge(f"file:{src_f}", f"file:{tgt_f}", edge_type="calls")

        logger.info(
            "Constructed code graph for '%s': %d nodes, %d edges",
            repo_name,
            g.number_of_nodes(),
            g.number_of_edges(),
        )
        return g

    def _resolve_import_target(
        self,
        current_file: str,
        target_import: str,
        module_to_file_map: dict[str, str],
        file_node_map: dict[str, str],
    ) -> str | None:
        """Resolves an import target string to an internal file node ID if internal."""
        # 1. Direct match in module_to_file_map
        if target_import in module_to_file_map:
            return file_node_map[module_to_file_map[target_import]]

        # 2. Dotted prefix match (e.g. from app.services.user_service.UserService)
        parts = target_import.split(".")
        for i in range(len(parts), 0, -1):
            candidate = ".".join(parts[:i])
            if candidate in module_to_file_map:
                return file_node_map[module_to_file_map[candidate]]

        # 3. Relative path resolution for JS/TS (e.g. ../models/user)
        if target_import.startswith("."):
            curr_dir = Path(current_file).parent
            candidate_path = (curr_dir / target_import).resolve()
            # Normalize to relative path
            for rel_path in file_node_map:
                p = Path(rel_path).resolve()
                if p.stem == candidate_path.stem and (
                    p.parent == candidate_path.parent or str(p).startswith(str(candidate_path))
                ):
                    return file_node_map[rel_path]

        return None

    def _resolve_symbol(
        self,
        target_name: str,
        symbol_qname_map: dict[str, str],
        symbol_short_map: dict[str, list[str]],
    ) -> str | None:
        """Resolves symbol by qualified or unqualified name."""
        if target_name in symbol_qname_map:
            return symbol_qname_map[target_name]
        matches = symbol_short_map.get(target_name)
        if matches and len(matches) == 1:
            return matches[0]
        return None


code_graph_builder = CodeGraphBuilder()
