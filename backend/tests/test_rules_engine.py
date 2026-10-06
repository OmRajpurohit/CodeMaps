from pathlib import Path

from backend.app.analyzers.registry import analyzer_registry
from backend.app.graph.builder import code_graph_builder
from backend.app.ingestion.detector import language_detector
from backend.app.rules.config import (
    ArchitectureRule,
    ArchitectureRulesConfig,
    LayerDefinition,
)
from backend.app.rules.engine import ArchitectureRuleEngine


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


def test_default_clean_architecture_detects_bad_controller():
    g = _build_test_graph()
    engine = ArchitectureRuleEngine()  # Default clean architecture rules

    violations = engine.evaluate_architecture(g)

    # bad_controller.py directly imports Database -> should be flagged as error
    layer_violations = [v for v in violations if v.rule_name == "Layer Boundary Violation"]
    assert len(layer_violations) >= 1

    bad_controller_violation = next(
        (v for v in layer_violations if "bad_controller" in v.source_file_path), None
    )
    assert bad_controller_violation is not None
    assert bad_controller_violation.severity == "error"
    assert bad_controller_violation.layer_from == "controller"
    assert bad_controller_violation.layer_to == "database"
    assert "Layer Violation" in bad_controller_violation.message


def test_custom_configurable_rules():
    g = _build_test_graph()

    # Custom rule: Disallow service from calling repository directly
    custom_config = ArchitectureRulesConfig(
        name="Strict Service Isolation",
        layers=[
            LayerDefinition(name="service", patterns=["**/services/**"]),
            LayerDefinition(name="repository", patterns=["**/repositories/**"]),
        ],
        rules=[
            ArchitectureRule(
                source_layer="service",
                target_layer="repository",
                allowed=False,
                severity="error",
                description="Custom strict rule: Services cannot directly access Repositories.",
            )
        ],
    )

    engine = ArchitectureRuleEngine(config=custom_config)
    violations = engine.evaluate_architecture(g)

    custom_violations = [v for v in violations if "Services cannot directly access Repositories" in v.message]
    assert len(custom_violations) >= 1
    assert any("user_service" in v.source_file_path for v in custom_violations)
