from pathlib import Path

import tree_sitter
import tree_sitter_javascript
import tree_sitter_typescript

from backend.app.analyzers.base import (
    BaseLanguageAnalyzer,
    FileAnalysisResult,
    ParsedEdge,
    ParsedSymbol,
)


class JavaScriptTypeScriptAnalyzer(BaseLanguageAnalyzer):
    """AST-based static code analyzer for JavaScript and TypeScript using Tree-sitter."""

    def __init__(self) -> None:
        self.js_language = tree_sitter.Language(tree_sitter_javascript.language())
        self.ts_language = tree_sitter.Language(tree_sitter_typescript.language_typescript())
        self.tsx_language = tree_sitter.Language(tree_sitter_typescript.language_tsx())

        self.js_parser = tree_sitter.Parser(self.js_language)
        self.ts_parser = tree_sitter.Parser(self.ts_language)
        self.tsx_parser = tree_sitter.Parser(self.tsx_language)

    @property
    def supported_languages(self) -> list[str]:
        return ["JavaScript", "TypeScript"]

    @property
    def supported_extensions(self) -> list[str]:
        return [".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"]

    def _get_parser_for_ext(self, ext: str) -> tree_sitter.Parser:
        if ext == ".tsx":
            return self.tsx_parser
        elif ext in {".ts"}:
            return self.ts_parser
        return self.js_parser

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
        ext = Path(rel_path).suffix.lower()
        parser = self._get_parser_for_ext(ext)
        tree = parser.parse(content)
        root_node = tree.root_node

        module_qname = self._module_path_from_rel_path(rel_path)
        is_ts = ext in {".ts", ".tsx"}
        language = "TypeScript" if is_ts else "JavaScript"

        symbols: list[ParsedSymbol] = []
        edges: list[ParsedEdge] = []

        # Line metrics calculation
        lines = content.decode("utf-8", errors="ignore").splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(
            1 for line in lines if line.strip().startswith("//") or line.strip().startswith("/*")
        )
        loc = max(0, total_lines - blank_lines - comment_lines)

        # Register Module Symbol
        symbols.append(
            ParsedSymbol(
                name=Path(rel_path).stem,
                qualified_name=module_qname,
                symbol_type="module",
                start_line=1,
                end_line=max(1, total_lines),
                metadata={"file_path": rel_path, "language": language},
            )
        )

        decision_count = 0

        def traverse(node: tree_sitter.Node, current_scope: str, current_class: str | None = None) -> None:
            nonlocal decision_count

            # Cyclomatic complexity decision points
            if node.type in {
                "if_statement",
                "for_statement",
                "for_in_statement",
                "while_statement",
                "do_statement",
                "switch_case",
                "catch_clause",
                "conditional_expression",
            }:
                decision_count += 1
            elif node.type == "binary_expression":
                # Check for logical operators &&, ||, ??
                for child in node.children:
                    if child.type in {"&&", "||", "??"}:
                        decision_count += 1
                        break

            # ES6 Import statement: import { x } from './y'
            if node.type == "import_statement":
                line_no = node.start_point.row + 1
                source_node = node.child_by_field_name("source")
                if source_node:
                    import_path = source_node.text.decode("utf-8").strip("'\"`")
                    edges.append(
                        ParsedEdge(
                            source=current_scope,
                            target=import_path,
                            edge_type="imports",
                            line_number=line_no,
                        )
                    )

            # CommonJS require('...')
            elif node.type == "call_expression":
                func_node = node.child_by_field_name("function")
                if func_node:
                    func_name = func_node.text.decode("utf-8")
                    line_no = node.start_point.row + 1
                    if func_name == "require":
                        args_node = node.child_by_field_name("arguments")
                        if args_node and len(args_node.children) > 1:
                            req_target = args_node.children[1].text.decode("utf-8").strip("'\"`")
                            edges.append(
                                ParsedEdge(
                                    source=current_scope,
                                    target=req_target,
                                    edge_type="imports",
                                    line_number=line_no,
                                )
                            )
                    elif func_name not in {"console.log", "console.error", "console.warn", "require"}:
                        edges.append(
                            ParsedEdge(
                                source=current_scope,
                                target=func_name,
                                edge_type="calls",
                                line_number=line_no,
                            )
                        )

            # Class Declaration
            elif node.type in {"class_declaration", "class"}:
                process_class(node, current_scope)
                return

            # Function Declaration
            elif node.type == "function_declaration":
                process_function(node, current_scope, current_class)
                return

            # TypeScript Interface Declaration
            elif node.type == "interface_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    if_name = name_node.text.decode("utf-8")
                    if_qname = f"{current_scope}.{if_name}"
                    start_line = node.start_point.row + 1
                    end_line = node.end_point.row + 1

                    symbols.append(
                        ParsedSymbol(
                            name=if_name,
                            qualified_name=if_qname,
                            symbol_type="interface",
                            start_line=start_line,
                            end_line=end_line,
                        )
                    )
                    edges.append(
                        ParsedEdge(
                            source=current_scope,
                            target=if_qname,
                            edge_type="contains",
                            line_number=start_line,
                        )
                    )

            # Export statement wrapping declarations
            elif node.type == "export_statement":
                for child in node.children:
                    if child.type in {"class_declaration", "function_declaration", "interface_declaration"}:
                        traverse(child, current_scope, current_class)
                    elif child.type == "lexical_declaration":
                        # e.g. export const myFunc = () => {}
                        process_lexical_declaration(child, current_scope)
                return

            # Method definition inside class body
            elif node.type == "method_definition":
                process_method(node, current_scope, current_class)
                return

            for child in node.children:
                traverse(child, current_scope, current_class)

        def process_class(node: tree_sitter.Node, parent_scope: str) -> None:
            name_node = node.child_by_field_name("name")
            if not name_node:
                # Find type_identifier or identifier in children
                for c in node.children:
                    if c.type in {"type_identifier", "identifier"}:
                        name_node = c
                        break
            if not name_node:
                return

            class_name = name_node.text.decode("utf-8")
            class_qname = f"{parent_scope}.{class_name}"
            start_line = node.start_point.row + 1
            end_line = node.end_point.row + 1

            superclasses: list[str] = []
            interfaces: list[str] = []

            # Check class heritage
            for child in node.children:
                if child.type == "class_heritage":
                    for heritage_clause in child.children:
                        if heritage_clause.type == "extends_clause":
                            for sc in heritage_clause.children:
                                if sc.type in {"identifier", "type_identifier", "member_expression"}:
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
                        elif heritage_clause.type == "implements_clause":
                            for iface in heritage_clause.children:
                                if iface.type in {"identifier", "type_identifier"}:
                                    iface_name = iface.text.decode("utf-8")
                                    interfaces.append(iface_name)
                                    edges.append(
                                        ParsedEdge(
                                            source=class_qname,
                                            target=iface_name,
                                            edge_type="implements",
                                            line_number=start_line,
                                        )
                                    )

            symbols.append(
                ParsedSymbol(
                    name=class_name,
                    qualified_name=class_qname,
                    symbol_type="class",
                    start_line=start_line,
                    end_line=end_line,
                    metadata={"superclasses": superclasses, "interfaces": interfaces},
                )
            )
            edges.append(
                ParsedEdge(
                    source=parent_scope,
                    target=class_qname,
                    edge_type="contains",
                    line_number=start_line,
                )
            )

            # Traverse class body
            body_node = node.child_by_field_name("body")
            if body_node:
                for child in body_node.children:
                    traverse(child, class_qname, current_class=class_name)

        def process_function(node: tree_sitter.Node, parent_scope: str, current_class: str | None) -> None:
            name_node = node.child_by_field_name("name")
            if not name_node:
                return
            func_name = name_node.text.decode("utf-8")
            func_qname = f"{parent_scope}.{func_name}"
            start_line = node.start_point.row + 1
            end_line = node.end_point.row + 1

            symbols.append(
                ParsedSymbol(
                    name=func_name,
                    qualified_name=func_qname,
                    symbol_type="function",
                    start_line=start_line,
                    end_line=end_line,
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

            body_node = node.child_by_field_name("body")
            if body_node:
                for child in body_node.children:
                    traverse(child, func_qname, current_class)

        def process_method(node: tree_sitter.Node, parent_scope: str, current_class: str | None) -> None:
            name_node = node.child_by_field_name("name")
            if not name_node:
                return
            method_name = name_node.text.decode("utf-8")
            method_qname = f"{parent_scope}.{method_name}"
            start_line = node.start_point.row + 1
            end_line = node.end_point.row + 1

            symbols.append(
                ParsedSymbol(
                    name=method_name,
                    qualified_name=method_qname,
                    symbol_type="method",
                    start_line=start_line,
                    end_line=end_line,
                    metadata={"parent_class": current_class},
                )
            )
            edges.append(
                ParsedEdge(
                    source=parent_scope,
                    target=method_qname,
                    edge_type="contains",
                    line_number=start_line,
                )
            )

            body_node = node.child_by_field_name("body")
            if body_node:
                for child in body_node.children:
                    traverse(child, method_qname, current_class)

        def process_lexical_declaration(node: tree_sitter.Node, parent_scope: str) -> None:
            # Handles const myFunc = () => { ... }
            for decl in node.children:
                if decl.type == "variable_declarator":
                    name_node = decl.child_by_field_name("name")
                    value_node = decl.child_by_field_name("value")
                    if name_node and value_node and value_node.type in {"arrow_function", "function"}:
                        func_name = name_node.text.decode("utf-8")
                        func_qname = f"{parent_scope}.{func_name}"
                        start_line = decl.start_point.row + 1
                        end_line = decl.end_point.row + 1

                        symbols.append(
                            ParsedSymbol(
                                name=func_name,
                                qualified_name=func_qname,
                                symbol_type="function",
                                start_line=start_line,
                                end_line=end_line,
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
                        traverse(value_node, func_qname, current_class=None)

        for child in root_node.children:
            traverse(child, module_qname)

        cyclomatic_complexity = float(max(1, 1 + decision_count))

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
