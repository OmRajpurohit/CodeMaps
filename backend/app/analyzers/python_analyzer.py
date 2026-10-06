from pathlib import Path

import tree_sitter
import tree_sitter_python

from backend.app.analyzers.base import (
    BaseLanguageAnalyzer,
    FileAnalysisResult,
    ParsedEdge,
    ParsedSymbol,
)


class PythonAnalyzer(BaseLanguageAnalyzer):
    """AST-based static code analyzer for Python using Tree-sitter."""

    def __init__(self) -> None:
        self.language = tree_sitter.Language(tree_sitter_python.language())
        self.parser = tree_sitter.Parser(self.language)

    @property
    def supported_languages(self) -> list[str]:
        return ["Python"]

    @property
    def supported_extensions(self) -> list[str]:
        return [".py"]

    def _module_path_from_rel_path(self, rel_path: str) -> str:
        """Converts 'backend/app/main.py' to 'backend.app.main'."""
        p = Path(rel_path)
        parts = list(p.parts[:-1]) + [p.stem]
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts) if parts else p.stem

    def parse_file(self, file_path: str, content: bytes, rel_path: str) -> FileAnalysisResult:
        tree = self.parser.parse(content)
        root_node = tree.root_node

        module_qname = self._module_path_from_rel_path(rel_path)
        symbols: list[ParsedSymbol] = []
        edges: list[ParsedEdge] = []

        # Calculate line metrics
        lines = content.decode("utf-8", errors="ignore").splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
        loc = max(0, total_lines - blank_lines - comment_lines)

        # Register Module Symbol
        symbols.append(
            ParsedSymbol(
                name=Path(rel_path).stem,
                qualified_name=module_qname,
                symbol_type="module",
                start_line=1,
                end_line=max(1, total_lines),
                metadata={"file_path": rel_path},
            )
        )

        decision_count = 0

        def traverse_and_extract(
            node: tree_sitter.Node,
            current_scope: str,
            current_class: str | None = None,
        ) -> None:
            nonlocal decision_count

            # Cyclomatic complexity decision points
            if node.type in {
                "if_statement",
                "elif_clause",
                "for_statement",
                "while_statement",
                "except_clause",
                "with_statement",
                "conditional_expression",
                "boolean_operator",
                "case_clause",
            }:
                decision_count += 1

            # Imports: import a, import a.b as c
            if node.type == "import_statement":
                line_no = node.start_point.row + 1
                for child in node.children:
                    if child.type == "dotted_name":
                        imported = child.text.decode("utf-8")
                        edges.append(
                            ParsedEdge(
                                source=current_scope,
                                target=imported,
                                edge_type="imports",
                                line_number=line_no,
                            )
                        )
                    elif child.type == "aliased_import":
                        name_node = child.child_by_field_name("name")
                        if name_node:
                            imported = name_node.text.decode("utf-8")
                            edges.append(
                                ParsedEdge(
                                    source=current_scope,
                                    target=imported,
                                    edge_type="imports",
                                    line_number=line_no,
                                )
                            )

            # From imports: from x.y import z
            elif node.type == "import_from_statement":
                line_no = node.start_point.row + 1
                module_name_node = node.child_by_field_name("module_name")
                base_module = module_name_node.text.decode("utf-8") if module_name_node else ""

                # Handle relative imports e.g. from . import x, from ..y import z
                dots_prefix = ""
                for child in node.children:
                    if child.type == "relative_import":
                        dots_prefix = child.text.decode("utf-8")
                        break

                if dots_prefix:
                    # Resolve relative import prefix
                    dot_count = dots_prefix.count(".")
                    parent_parts = module_qname.split(".")
                    if len(parent_parts) >= dot_count:
                        resolved_prefix = ".".join(parent_parts[:-dot_count])
                        base_module = f"{resolved_prefix}.{base_module}".strip(".")
                    else:
                        base_module = dots_prefix + base_module

                for child in node.children:
                    if child.type in {"dotted_name", "aliased_import", "identifier"}:
                        if child == module_name_node:
                            continue
                        name_text = child.text.decode("utf-8")
                        if child.type == "aliased_import":
                            alias_name = child.child_by_field_name("name")
                            if alias_name:
                                name_text = alias_name.text.decode("utf-8")

                        target_symbol = f"{base_module}.{name_text}" if base_module else name_text
                        edges.append(
                            ParsedEdge(
                                source=current_scope,
                                target=target_symbol,
                                edge_type="imports",
                                line_number=line_no,
                            )
                        )

            # Decorated definition (class or function with @decorator)
            elif node.type == "decorated_definition":
                decorators: list[str] = []
                for child in node.children:
                    if child.type == "decorator":
                        decorators.append(child.text.decode("utf-8"))
                    elif child.type in {"class_definition", "function_definition"}:
                        process_definition(child, current_scope, current_class, decorators)
                return

            # Class definition without decorator
            elif node.type == "class_definition":
                process_definition(node, current_scope, current_class, decorators=[])
                return

            # Function definition without decorator
            elif node.type == "function_definition":
                process_definition(node, current_scope, current_class, decorators=[])
                return

            # Function/Method Call
            elif node.type == "call":
                func_node = node.child_by_field_name("function")
                if func_node:
                    called_name = func_node.text.decode("utf-8")
                    line_no = node.start_point.row + 1
                    # Avoid recording primitive/built-in trivial noise
                    if called_name not in {"print", "len", "range", "isinstance", "str", "int", "float", "bool", "dict", "list", "set", "tuple"}:
                        edges.append(
                            ParsedEdge(
                                source=current_scope,
                                target=called_name,
                                edge_type="calls",
                                line_number=line_no,
                            )
                        )

            # Traverse child nodes
            for child in node.children:
                traverse_and_extract(child, current_scope, current_class)

        def process_definition(
            def_node: tree_sitter.Node,
            parent_scope: str,
            parent_class: str | None,
            decorators: list[str],
        ) -> None:
            nonlocal decision_count
            name_node = def_node.child_by_field_name("name")
            if not name_node:
                return
            name = name_node.text.decode("utf-8")
            start_line = def_node.start_point.row + 1
            end_line = def_node.end_point.row + 1

            if def_node.type == "class_definition":
                class_qname = f"{parent_scope}.{name}"
                # Extract superclasses
                superclasses: list[str] = []
                superclasses_node = def_node.child_by_field_name("superclasses")
                if superclasses_node:
                    for sc in superclasses_node.children:
                        if sc.type in {"identifier", "attribute"}:
                            sc_name = sc.text.decode("utf-8")
                            superclasses.append(sc_name)
                            edges.append(
                                ParsedEdge(
                                    source=class_qname,
                                    target=sc_name,
                                    edge_type="inherits",
                                    line_number=start_line,
                                )
                            )

                symbols.append(
                    ParsedSymbol(
                        name=name,
                        qualified_name=class_qname,
                        symbol_type="class",
                        start_line=start_line,
                        end_line=end_line,
                        metadata={"decorators": decorators, "superclasses": superclasses},
                    )
                )
                # Parent contains class
                edges.append(
                    ParsedEdge(
                        source=parent_scope,
                        target=class_qname,
                        edge_type="contains",
                        line_number=start_line,
                    )
                )

                # Process class body
                body_node = def_node.child_by_field_name("body")
                if body_node:
                    for child in body_node.children:
                        traverse_and_extract(child, class_qname, current_class=name)

            elif def_node.type == "function_definition":
                symbol_type = "method" if parent_class else "function"
                func_qname = f"{parent_scope}.{name}"

                # Extract parameters
                params: list[str] = []
                params_node = def_node.child_by_field_name("parameters")
                if params_node:
                    for p in params_node.children:
                        if p.type in {"identifier", "typed_parameter", "default_parameter"}:
                            params.append(p.text.decode("utf-8"))

                symbols.append(
                    ParsedSymbol(
                        name=name,
                        qualified_name=func_qname,
                        symbol_type=symbol_type,
                        start_line=start_line,
                        end_line=end_line,
                        metadata={
                            "decorators": decorators,
                            "parameters": params,
                            "parent_class": parent_class,
                        },
                    )
                )
                edges.append(
                    ParsedEdge(
                        source=parent_scope,
                        target=func_qname,
                        edge_type="contains",
                        line_number=start_line,
                    )
                )

                # Process function body
                body_node = def_node.child_by_field_name("body")
                if body_node:
                    for child in body_node.children:
                        traverse_and_extract(child, func_qname, current_class=parent_class)

        # Start traversal from root node with module scope
        for child in root_node.children:
            traverse_and_extract(child, module_qname)

        cyclomatic_complexity = float(max(1, 1 + decision_count))

        return FileAnalysisResult(
            file_path=rel_path,
            language="Python",
            loc=loc,
            blank_lines=blank_lines,
            comment_lines=comment_lines,
            cyclomatic_complexity=cyclomatic_complexity,
            symbols=symbols,
            edges=edges,
        )
