from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParsedSymbol:
    name: str
    qualified_name: str
    symbol_type: str  # module, package, class, function, method, interface
    start_line: int
    end_line: int
    docstring: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedEdge:
    source: str
    target: str
    edge_type: str  # imports, calls, inherits, implements, contains
    line_number: int | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileAnalysisResult:
    file_path: str
    language: str
    loc: int
    blank_lines: int
    comment_lines: int
    cyclomatic_complexity: float
    symbols: list[ParsedSymbol] = field(default_factory=list)
    edges: list[ParsedEdge] = field(default_factory=list)


class BaseLanguageAnalyzer(ABC):
    """Abstract base class for all language AST analyzers."""

    @property
    @abstractmethod
    def supported_languages(self) -> list[str]:
        """List of human-readable language names supported."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """List of lowercase file extensions supported (e.g. ['.py'])."""
        pass

    def can_analyze(self, file_path: str) -> bool:
        """Determines if this analyzer can handle the given file path."""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions

    @abstractmethod
    def parse_file(self, file_path: str, content: bytes, rel_path: str) -> FileAnalysisResult:
        """
        Parses source file content using Tree-sitter AST, extracting
        symbols, relationships (imports, calls, inheritance), and metrics.
        """
        pass
