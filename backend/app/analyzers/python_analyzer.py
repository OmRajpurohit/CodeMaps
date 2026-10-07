import ast
from pathlib import Path

from backend.app.analyzers.base import (
    BaseLanguageAnalyzer,
    FileAnalysisResult,
    ParsedEdge,
    ParsedSymbol,
)


class PythonAnalyzer(BaseLanguageAnalyzer):
    """AST-based static code analyzer for Python using Python standard library ast."""

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
        source_text = content.decode("utf-8", errors="ignore")
        lines = source_text.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
        loc = max(0, total_lines - blank_lines - comment_lines)

        module_qname = self._module_path_from_rel_path(rel_path)
        symbols: list[ParsedSymbol] = [
            ParsedSymbol(
                name=Path(rel_path).stem,
                qualified_name=module_qname,
                symbol_type="module",
                start_line=1,
                end_line=max(1, total_lines),
                metadata={"file_path": rel_path},
            )
        ]
        edges: list[ParsedEdge] = []

        try:
            tree = ast.parse(source_text, filename=rel_path)
        except SyntaxError:
            return FileAnalysisResult(
                file_path=rel_path,
                language="Python",
                loc=loc,
                blank_lines=blank_lines,
                comment_lines=comment_lines,
                cyclomatic_complexity=1.0,
                symbols=symbols,
                edges=edges,
            )

        decision_count = 0
        skip_primitives = {
            "print",
            "len",
            "range",
            "isinstance",
            "str",
            "int",
            "float",
            "bool",
            "dict",
            "list",
            "set",
            "tuple",
        }

        def get_decorators(decorator_list: list[ast.AST]) -> list[str]:
            res = []
            for d in decorator_list:
                try:
                    res.append(f"@{ast.unparse(d)}")
                except Exception:
                    pass
            return res

        def walk_node(
            node: ast.AST, current_scope: str, current_class: str | None = None
        ) -> None:
            nonlocal decision_count

            # Cyclomatic complexity decision points
            if isinstance(
                node,
                (
                    ast.If,
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                    ast.ExceptHandler,
                    ast.With,
                    ast.AsyncWith,
                    ast.IfExp,
                    getattr(ast, "match_case", ()),
                ),
            ):
                decision_count += 1
            elif isinstance(node, ast.BoolOp):
                decision_count += max(1, len(node.values) - 1)

            # Imports: import a, import a.b as c
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported = alias.name
                    edges.append(
                        ParsedEdge(
                            source=current_scope,
                            target=imported,
                            edge_type="imports",
                            line_number=node.lineno,
                        )
                    )

            # From imports: from x.y import z
            elif isinstance(node, ast.ImportFrom):
                base_module = node.module or ""
                if node.level and node.level > 0:
                    parent_parts = module_qname.split(".")
                    if len(parent_parts) >= node.level:
                        resolved_prefix = ".".join(parent_parts[: -node.level])
                        base_module = f"{resolved_prefix}.{base_module}".strip(".")
                    else:
                        base_module = ("." * node.level) + base_module

                for alias in node.names:
                    target_symbol = (
                        f"{base_module}.{alias.name}" if base_module else alias.name
                    )
                    edges.append(
                        ParsedEdge(
                            source=current_scope,
                            target=target_symbol,
                            edge_type="imports",
                            line_number=node.lineno,
                        )
                    )

            # Class definition
            elif isinstance(node, ast.ClassDef):
                class_qname = f"{current_scope}.{node.name}"
                superclasses = []
                for base in node.bases:
                    try:
                        sc_name = ast.unparse(base)
                    except Exception:
                        sc_name = getattr(base, "id", "")
                    if sc_name:
                        superclasses.append(sc_name)
                        edges.append(
                            ParsedEdge(
                                source=class_qname,
                                target=sc_name,
                                edge_type="inherits",
                                line_number=node.lineno,
                            )
                        )

                symbols.append(
                    ParsedSymbol(
                        name=node.name,
                        qualified_name=class_qname,
                        symbol_type="class",
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        metadata={
                            "decorators": get_decorators(node.decorator_list),
                            "superclasses": superclasses,
                        },
                    )
                )
                edges.append(
                    ParsedEdge(
                        source=current_scope,
                        target=class_qname,
                        edge_type="contains",
                        line_number=node.lineno,
                    )
                )

                for item in node.body:
                    walk_node(item, class_qname, current_class=node.name)
                return

            # Function definition
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbol_type = "method" if current_class else "function"
                func_qname = f"{current_scope}.{node.name}"

                params = [arg.arg for arg in node.args.args]
                if node.args.vararg:
                    params.append(f"*{node.args.vararg.arg}")
                params.extend(arg.arg for arg in node.args.kwonlyargs)
                if node.args.kwarg:
                    params.append(f"**{node.args.kwarg.arg}")

                symbols.append(
                    ParsedSymbol(
                        name=node.name,
                        qualified_name=func_qname,
                        symbol_type=symbol_type,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        metadata={
                            "decorators": get_decorators(node.decorator_list),
                            "parameters": params,
                            "parent_class": current_class,
                        },
                    )
                )
                edges.append(
                    ParsedEdge(
                        source=current_scope,
                        target=func_qname,
                        edge_type="contains",
                        line_number=node.lineno,
                    )
                )

                for item in node.body:
                    walk_node(item, func_qname, current_class=current_class)
                return

            # Function Call
            elif isinstance(node, ast.Call):
                try:
                    called_name = ast.unparse(node.func)
                    if called_name and called_name not in skip_primitives:
                        edges.append(
                            ParsedEdge(
                                source=current_scope,
                                target=called_name,
                                edge_type="calls",
                                line_number=node.lineno,
                            )
                        )
                except Exception:
                    pass

            for child in ast.iter_child_nodes(node):
                walk_node(child, current_scope, current_class)

        for stmt in tree.body:
            walk_node(stmt, module_qname)

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
