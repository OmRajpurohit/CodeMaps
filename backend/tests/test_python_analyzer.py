from pathlib import Path

from backend.app.analyzers.python_analyzer import PythonAnalyzer


def test_python_analyzer_user_repository():
    analyzer = PythonAnalyzer()
    file_path = "fixtures/python_project/app/repositories/user_repository.py"
    content = Path(file_path).read_bytes()

    result = analyzer.parse_file(file_path, content, rel_path="app/repositories/user_repository.py")

    assert result.language == "Python"
    assert result.loc > 0
    assert result.cyclomatic_complexity >= 1.0

    # Verify Symbols: module, BaseRepository, UserRepository, methods
    symbol_names = [s.name for s in result.symbols]
    assert "user_repository" in symbol_names
    assert "BaseRepository" in symbol_names
    assert "UserRepository" in symbol_names
    assert "find_by_id" in symbol_names

    # Verify Inherits edge: UserRepository inherits BaseRepository
    inherits_edges = [e for e in result.edges if e.edge_type == "inherits"]
    assert any(
        e.source.endswith("UserRepository") and e.target == "BaseRepository"
        for e in inherits_edges
    )

    # Verify Imports: Database from app.db.database
    imports_edges = [e for e in result.edges if e.edge_type == "imports"]
    assert any("app.db.database" in e.target for e in imports_edges)


def test_python_analyzer_user_controller_decorators_and_calls():
    analyzer = PythonAnalyzer()
    file_path = "fixtures/python_project/app/controllers/user_controller.py"
    content = Path(file_path).read_bytes()

    result = analyzer.parse_file(file_path, content, rel_path="app/controllers/user_controller.py")

    method_sym = next(s for s in result.symbols if s.name == "get_user_profile")
    assert method_sym.symbol_type == "method"
    assert len(method_sym.metadata.get("decorators", [])) > 0
    assert any("get(" in d for d in method_sym.metadata["decorators"])

    # Verify calls
    calls = [e for e in result.edges if e.edge_type == "calls"]
    assert any("self.service.get_user" in c.target for c in calls)
