
from backend.app.analyzers.base import BaseLanguageAnalyzer, FileAnalysisResult
from backend.app.analyzers.javascript_analyzer import JavaScriptTypeScriptAnalyzer
from backend.app.analyzers.python_analyzer import PythonAnalyzer
from backend.app.core.logging import logger


class AnalyzerRegistry:
    """
    Plugin-based registry for language analyzers.
    Enables adding future language parsers (Go, Java, Rust) without modifying core pipeline.
    """

    def __init__(self) -> None:
        self._analyzers: list[BaseLanguageAnalyzer] = []
        self._ext_map: dict[str, BaseLanguageAnalyzer] = {}

    def register(self, analyzer: BaseLanguageAnalyzer) -> None:
        """Registers a language analyzer plugin."""
        self._analyzers.append(analyzer)
        for ext in analyzer.supported_extensions:
            self._ext_map[ext.lower()] = analyzer
        logger.info(
            "Registered analyzer for %s (extensions: %s)",
            ", ".join(analyzer.supported_languages),
            ", ".join(analyzer.supported_extensions),
        )

    def get_analyzer_for_file(self, file_path: str) -> BaseLanguageAnalyzer | None:
        """Finds the appropriate analyzer for the given file path based on extension."""
        for ext, analyzer in self._ext_map.items():
            if file_path.lower().endswith(ext):
                return analyzer
        return None

    def analyze_file(self, file_path: str, content: bytes, rel_path: str) -> FileAnalysisResult | None:
        """Dispatches file parsing to the registered analyzer plugin."""
        analyzer = self.get_analyzer_for_file(file_path)
        if not analyzer:
            return None
        return analyzer.parse_file(file_path, content, rel_path)


# Default registry instance configured with Python and JavaScript/TypeScript analyzers
analyzer_registry = AnalyzerRegistry()
analyzer_registry.register(PythonAnalyzer())
analyzer_registry.register(JavaScriptTypeScriptAnalyzer())
