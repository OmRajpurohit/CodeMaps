from pathlib import Path

import networkx as nx

from backend.app.analyzers.registry import analyzer_registry
from backend.app.diff.analyzer import architecture_diff_analyzer
from backend.app.graph.builder import code_graph_builder
from backend.app.impact.analyzer import impact_analyzer
from backend.app.ingestion.detector import language_detector


def _get_fixture_graph():
    fixture_dir = Path("fixtures/python_project")
    structure = language_detector.scan_repository(fixture_dir)

    analysis_results = []
    for f in structure.files:
        content = Path(f.path).read_bytes()
        res = analyzer_registry.analyze_file(f.path, content, f.relative_path)
        if res:
            analysis_results.append(res)

    return code_graph_builder.build_graph("python_project", analysis_results)


def test_impact_analysis_database_blast_radius():
    g = _get_fixture_graph()
    target_node = "file:app/db/database.py"

    res = impact_analyzer.analyze_impact(g, target_node)

    assert res.target_node_id == target_node
    assert res.direct_dependents_count == 2  # user_repository.py, bad_controller.py
    assert res.transitive_dependents_count >= 2  # user_service.py, user_controller.py
    assert res.impact_score > 0.0

    affected_names = [n.name for n in res.affected_nodes]
    assert "user_repository.py" in affected_names
    assert "user_service.py" in affected_names
    assert "user_controller.py" in affected_names

    # Check dependency chain contains database -> repository -> service -> controller
    found_chain = False
    for chain in res.dependency_chain:
        has_controller = any("user_controller" in item for item in chain)
        has_db = any("database" in item for item in chain)
        if has_controller and has_db:
            found_chain = True
            break
    assert found_chain


def test_architecture_diff_detects_introduced_cycles():
    g_base = nx.MultiDiGraph()
    g_base.add_node("file:service_a.py", data=None)
    g_base.add_node("file:service_b.py", data=None)
    g_base.add_edge("file:service_a.py", "file:service_b.py", edge_type="imports")

    # In target graph, a cycle is created: B imports A!
    g_target = g_base.copy()
    g_target.add_edge("file:service_b.py", "file:service_a.py", edge_type="imports")

    diff = architecture_diff_analyzer.diff_graphs(g_base, g_target, "v1.0", "v1.1")

    assert len(diff.dependencies_added) == 1
    assert len(diff.new_cycles_introduced) == 1
    assert diff.risk_level in {"HIGH", "CRITICAL"}
    assert any("circular dependency" in s for s in diff.risk_summary)
