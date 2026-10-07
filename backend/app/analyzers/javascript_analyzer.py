import re
from pathlib import Path

from backend.app.analyzers.base import (
    BaseLanguageAnalyzer,
    FileAnalysisResult,
    ParsedEdge,
    ParsedSymbol,
)


class JavaScriptTypeScriptAnalyzer(BaseLanguageAnalyzer):
    """
    Robust static code analyzer for JavaScript and TypeScript.
    Extracts modules, classes, interfaces, methods, functions, inheritance,
    imports, call graphs, and cyclomatic complexity without native crash risks.
    """

    @property
    def supported_languages(self) -> list[str]:
        return ["JavaScript", "TypeScript"]

    @property
    def supported_extensions(self) -> list[str]:
        return [".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"]

    def _module_path_from_rel_path(self, rel_path: str) -> str:
        """Converts 'src/services/userService.ts' to 'src/services/userService'."""
        p = Path(rel_path)
        stem = p.stem
        if stem in {"index", "default"}:
            parts = list(p.parts[:-1])
            return "/".join(parts) if parts else stem
        parts = list(p.parts[:-1]) + [stem]
        return "/".join(parts)

    def parse_file(self, file_path: str, content: bytes, rel_path: str) -> FileAnalysisResult:
        source_text = content.decode("utf-8", errors="ignore")
        lines = source_text.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(
            1
            for line in lines
            if line.strip().startswith("//")
            or line.strip().startswith("/*")
            or line.strip().startswith("*")
        )
        loc = max(0, total_lines - blank_lines - comment_lines)

        ext = Path(rel_path).suffix.lower()
        is_ts = ext in {".ts", ".tsx"}
        language = "TypeScript" if is_ts else "JavaScript"
        module_qname = self._module_path_from_rel_path(rel_path)

        symbols: list[ParsedSymbol] = [
            ParsedSymbol(
                name=Path(rel_path).stem,
                qualified_name=module_qname,
                symbol_type="module",
                start_line=1,
                end_line=max(1, total_lines),
                metadata={"file_path": rel_path, "language": language},
            )
        ]
        edges: list[ParsedEdge] = []

        # 1. Cyclomatic Complexity
        # Count decision keywords and logical operators
        decision_patterns = [
            r"\bif\b",
            r"\belse\s+if\b",
            r"\bfor\b",
            r"\bwhile\b",
            r"\bcase\b",
            r"\bcatch\b",
            r"\bdo\b",
            r"\?",
            r"&&",
            r"\|\|",
            r"\?\?",
        ]
        decision_count = 0
        for pattern in decision_patterns:
            decision_count += len(re.findall(pattern, source_text))
        cyclomatic_complexity = float(max(1, 1 + decision_count))

        # 2. Extract Imports (ES6, CommonJS, dynamic import)
        import_re = re.compile(
            r"""(?:import\s+(?:(?:[\w*\s{},$]+)\s+from\s+)?['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\)|import\s*\(\s*['"]([^'"]+)['"]\s*\))"""
        )
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue
            for match in import_re.finditer(line):
                target = match.group(1) or match.group(2) or match.group(3)
                if target:
                    edges.append(
                        ParsedEdge(
                            source=module_qname,
                            target=target,
                            edge_type="imports",
                            line_number=idx,
                        )
                    )

        # 3. Regular Expressions for Declarations
        # export class Foo extends Bar implements Baz, Qux {
        class_re = re.compile(
            r"^(?:export\s+)?(?:default\s+)?class\s+([A-Za-z0-9_$]+)(?:\s+extends\s+([A-Za-z0-9_$.]+))?(?:\s+implements\s+([A-Za-z0-9_$,\s]+))?"
        )
        # export interface Foo extends Bar {
        interface_re = re.compile(
            r"^(?:export\s+)?interface\s+([A-Za-z0-9_$]+)(?:\s+extends\s+([A-Za-z0-9_$,\s]+))?"
        )
        # function funcName(...)
        func_re = re.compile(
            r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\("
        )
        # const/let/var funcName = (async)? (...) => or function
        var_func_re = re.compile(
            r"^(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z0-9_$]+)\s*=>"
        )
        # Method inside class: methodName(...) {
        method_re = re.compile(
            r"^(?:public\s+|private\s+|protected\s+|static\s+|async\s+|get\s+|set\s+)*([A-Za-z0-9_$]+)\s*\([^)]*\)\s*(?::\s*[^;{]+)?\s*\{"
        )

        current_class: str | None = None
        current_class_qname: str | None = None
        class_brace_depth = 0
        current_brace_depth = 0

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith("//")
                or stripped.startswith("/*")
                or stripped.startswith("*")
            ):
                continue

            # Check interface
            if_match = interface_re.match(stripped)
            if if_match:
                if_name = if_match.group(1)
                if_qname = f"{module_qname}.{if_name}"
                symbols.append(
                    ParsedSymbol(
                        name=if_name,
                        qualified_name=if_qname,
                        symbol_type="interface",
                        start_line=idx,
                        end_line=idx,
                    )
                )
                edges.append(
                    ParsedEdge(
                        source=module_qname,
                        target=if_qname,
                        edge_type="contains",
                        line_number=idx,
                    )
                )
                if if_match.group(2):
                    for parent_if in [
                        p.strip() for p in if_match.group(2).split(",") if p.strip()
                    ]:
                        edges.append(
                            ParsedEdge(
                                source=if_qname,
                                target=parent_if,
                                edge_type="inherits",
                                line_number=idx,
                            )
                        )

            # Check class
            class_match = class_re.match(stripped)
            if class_match:
                class_name = class_match.group(1)
                class_qname = f"{module_qname}.{class_name}"
                current_class = class_name
                current_class_qname = class_qname
                class_brace_depth = current_brace_depth + (line.count("{") - line.count("}"))
                superclasses = []
                interfaces = []
                if class_match.group(2):
                    sc = class_match.group(2).strip()
                    superclasses.append(sc)
                    edges.append(
                        ParsedEdge(
                            source=class_qname,
                            target=sc,
                            edge_type="inherits",
                            line_number=idx,
                        )
                    )
                if class_match.group(3):
                    for iface in [
                        i.strip() for i in class_match.group(3).split(",") if i.strip()
                    ]:
                        interfaces.append(iface)
                        edges.append(
                            ParsedEdge(
                                source=class_qname,
                                target=iface,
                                edge_type="implements",
                                line_number=idx,
                            )
                        )

                symbols.append(
                    ParsedSymbol(
                        name=class_name,
                        qualified_name=class_qname,
                        symbol_type="class",
                        start_line=idx,
                        end_line=idx,
                        metadata={"superclasses": superclasses, "interfaces": interfaces},
                    )
                )
                edges.append(
                    ParsedEdge(
                        source=module_qname,
                        target=class_qname,
                        edge_type="contains",
                        line_number=idx,
                    )
                )

            # Check function declaration
            func_match = func_re.match(stripped)
            if func_match and not class_match:
                func_name = func_match.group(1)
                func_qname = f"{module_qname}.{func_name}"
                symbols.append(
                    ParsedSymbol(
                        name=func_name,
                        qualified_name=func_qname,
                        symbol_type="function",
                        start_line=idx,
                        end_line=idx,
                    )
                )
                edges.append(
                    ParsedEdge(
                        source=module_qname,
                        target=func_qname,
                        edge_type="contains",
                        line_number=idx,
                    )
                )

            # Check variable function (const foo = () => {})
            var_func_match = var_func_re.match(stripped)
            if var_func_match and not class_match and not func_match:
                func_name = var_func_match.group(1)
                func_qname = f"{module_qname}.{func_name}"
                symbols.append(
                    ParsedSymbol(
                        name=func_name,
                        qualified_name=func_qname,
                        symbol_type="function",
                        start_line=idx,
                        end_line=idx,
                    )
                )
                edges.append(
                    ParsedEdge(
                        source=module_qname,
                        target=func_qname,
                        edge_type="contains",
                        line_number=idx,
                    )
                )

            # Check method inside class
            if current_class and current_brace_depth >= class_brace_depth - 1:
                method_match = method_re.match(stripped)
                if (
                    method_match
                    and not class_match
                    and not stripped.startswith("if")
                    and not stripped.startswith("while")
                    and not stripped.startswith("switch")
                ):
                    m_name = method_match.group(1)
                    if m_name not in {"if", "for", "while", "catch", "switch", "return"}:
                        m_qname = f"{current_class_qname}.{m_name}"
                        symbols.append(
                            ParsedSymbol(
                                name=m_name,
                                qualified_name=m_qname,
                                symbol_type="method",
                                start_line=idx,
                                end_line=idx,
                                metadata={"parent_class": current_class},
                            )
                        )
                        edges.append(
                            ParsedEdge(
                                source=current_class_qname,
                                target=m_qname,
                                edge_type="contains",
                                line_number=idx,
                            )
                        )

            # Track brace depth
            current_brace_depth += line.count("{") - line.count("}")
            if current_class and current_brace_depth < class_brace_depth:
                current_class = None
                current_class_qname = None

            # Calls
            call_matches = re.finditer(r"\b([A-Za-z0-9_$.]+)\s*\(", line)
            for cm in call_matches:
                called = cm.group(1).strip()
                if (
                    called
                    not in {
                        "if",
                        "for",
                        "while",
                        "catch",
                        "switch",
                        "function",
                        "return",
                        "require",
                        "console.log",
                        "console.error",
                        "console.warn",
                        "import",
                    }
                    and not called.endswith(".forEach")
                    and not called.endswith(".map")
                ):
                    caller = current_class_qname or module_qname
                    edges.append(
                        ParsedEdge(
                            source=caller,
                            target=called,
                            edge_type="calls",
                            line_number=idx,
                        )
                    )

        return FileAnalysisResult(
            file_path=rel_path,
            language=language,
            loc=loc,
            blank_lines=blank_lines,
            comment_lines=comment_lines,
            cyclomatic_complexity=cyclomatic_complexity,
            symbols=symbols,
            edges=edges,
        )
