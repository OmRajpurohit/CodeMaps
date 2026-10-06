from backend.app.analyzers.javascript_analyzer import JavaScriptTypeScriptAnalyzer
from backend.app.analyzers.python_analyzer import PythonAnalyzer
from backend.app.analyzers.registry import analyzer_registry


def test_registry_dispatch():
    py_analyzer = analyzer_registry.get_analyzer_for_file("app/main.py")
    assert isinstance(py_analyzer, PythonAnalyzer)

    ts_analyzer = analyzer_registry.get_analyzer_for_file("src/index.ts")
    assert isinstance(ts_analyzer, JavaScriptTypeScriptAnalyzer)

    tsx_analyzer = analyzer_registry.get_analyzer_for_file("components/App.tsx")
    assert isinstance(tsx_analyzer, JavaScriptTypeScriptAnalyzer)

    unknown = analyzer_registry.get_analyzer_for_file("data.unsupported")
    assert unknown is None
