from pathlib import Path

from backend.app.analyzers.registry import analyzer_registry
from backend.app.graph.algorithms import graph_algorithms
from backend.app.graph.builder import code_graph_builder
from backend.app.ingestion.detector import language_detector


def _build_test_graph():
    fixture_dir = Path("fixtures/python_project")
    structure = language_detector.scan_repository(fixture_dir)

    analysis_results = []
    for f in structure.files:
        content = Path(f.path).read_bytes()
        res = analyzer_registry.analyze_file(f.path, content, f.relative_path)
        if res:
            analysis_results.append(res)

    return code_graph_builder.build_graph("python_project", analysis_results)


def test_graph_construction_nodes_and_edges():
    g = _build_test_graph()

    assert g.number_of_nodes() > 10
    assert g.number_of_edges() > 10

    # Verify repository root node exists
    assert "repo:python_project" in g

    # Verify containment edges exist
    contains_edges = [
        (u, v) for u, v, d in g.edges(data=True) if d.get("edge_type") == "contains"
    ]
    assert len(contains_edges) > 5

    # Verify file nodes exist
    assert "file:app/db/database.py" in g
    assert "file:app/repositories/user_repository.py" in g
    assert "file:app/services/user_service.py" in g
    assert "file:app/controllers/user_controller.py" in g


def test_tarjan_scc_and_cycle_detection():
    g = _build_test_graph()

    # 1. Test Tarjan's SCC
    sccs = graph_algorithms.detect_scc(g)
    assert len(sccs) >= 1

    # Find the circular cluster containing modules a, b, c
    circular_scc = next((s for s in sccs if s.size == 3), None)
    assert circular_scc is not None
    scc_nodes_str = " ".join(circular_scc.nodes)
    assert "module_a" in scc_nodes_str
    assert "module_b" in scc_nodes_str
    assert "module_c" in scc_nodes_str

    # 2. Test Cycle Detection
    cycles = graph_algorithms.detect_cycles(g)
    assert len(cycles) >= 1
    # Verify that cycle description mentions modules
    cycle_desc = cycles[0].description
    assert "module_" in cycle_desc


def test_graph_metrics_calculation():
    g = _build_test_graph()
    metrics = graph_algorithms.compute_metrics(g)

    # database.py should have fan-in > 0 (it is imported by user_repository and bad_controller)
    db_node = "file:app/db/database.py"
    assert db_node in metrics.fan_in
    assert metrics.fan_in[db_node] >= 2

    # Database is stable: fan_out is 0, so instability is 0.0
    assert metrics.fan_out[db_node] == 0
    assert metrics.instability[db_node] == 0.0

    # User controller has fan-out > 0 (imports UserService)
    controller_node = "file:app/controllers/user_controller.py"
    assert metrics.fan_out[controller_node] >= 1
    assert metrics.instability[controller_node] > 0.0


def test_reverse_dependency_bfs_traversal():
    g = _build_test_graph()

    # What is affected if database.py changes?
    db_node = "file:app/db/database.py"
    dependents = graph_algorithms.reverse_bfs_traversal(g, db_node)

    # Direct dependents: user_repository.py and bad_controller.py
    assert "file:app/repositories/user_repository.py" in dependents
    assert dependents["file:app/repositories/user_repository.py"] == 1

    assert "file:app/violations/bad_controller.py" in dependents
    assert dependents["file:app/violations/bad_controller.py"] == 1

    # Transitive dependents: user_service.py (depth 2), user_controller.py (depth 3)
    assert "file:app/services/user_service.py" in dependents
    assert dependents["file:app/services/user_service.py"] == 2

    assert "file:app/controllers/user_controller.py" in dependents
    assert dependents["file:app/controllers/user_controller.py"] == 3
