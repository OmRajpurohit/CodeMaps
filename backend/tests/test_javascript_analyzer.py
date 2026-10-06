from pathlib import Path

from backend.app.analyzers.javascript_analyzer import JavaScriptTypeScriptAnalyzer


def test_ts_analyzer_user_model():
    analyzer = JavaScriptTypeScriptAnalyzer()
    file_path = "fixtures/ts_project/src/models/user.ts"
    content = Path(file_path).read_bytes()

    result = analyzer.parse_file(file_path, content, rel_path="src/models/user.ts")

    assert result.language == "TypeScript"
    assert result.loc > 0

    symbol_names = [s.name for s in result.symbols]
    assert "User" in symbol_names
    assert "BaseEntity" in symbol_names

    user_iface = next(s for s in result.symbols if s.name == "User")
    assert user_iface.symbol_type == "interface"


def test_ts_analyzer_user_service_heritage():
    analyzer = JavaScriptTypeScriptAnalyzer()
    file_path = "fixtures/ts_project/src/services/userService.ts"
    content = Path(file_path).read_bytes()

    result = analyzer.parse_file(file_path, content, rel_path="src/services/userService.ts")

    # Check symbols: UserService, IUserService, getUser
    symbol_names = [s.name for s in result.symbols]
    assert "UserService" in symbol_names
    assert "IUserService" in symbol_names
    assert "getUser" in symbol_names

    # Check extends BaseEntity -> inherits edge
    inherits_edges = [e for e in result.edges if e.edge_type == "inherits"]
    assert any("BaseEntity" in e.target for e in inherits_edges)

    # Check implements IUserService -> implements edge
    implements_edges = [e for e in result.edges if e.edge_type == "implements"]
    assert any("IUserService" in e.target for e in implements_edges)

    # Check ES6 import edge
    imports_edges = [e for e in result.edges if e.edge_type == "imports"]
    assert any("../models/user" in e.target for e in imports_edges)
