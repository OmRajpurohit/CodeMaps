from pathlib import Path

import git

from backend.app.analyzers.registry import analyzer_registry
from backend.app.git.analyzer import FileChurnMetric, GitHistoryAnalyzer
from backend.app.graph.algorithms import graph_algorithms
from backend.app.graph.builder import code_graph_builder
from backend.app.hotspots.engine import HotspotEngine
from backend.app.ingestion.detector import language_detector


def test_git_history_analyzer_with_synthetic_repo(tmp_path: Path):
    # Initialize a temporary Git repo with commits
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    repo = git.Repo.init(repo_dir)

    # Commit 1: add file1
    file1 = repo_dir / "service.py"
    file1.write_text("def run(): pass\n", encoding="utf-8")
    repo.index.add(["service.py"])
    repo.index.commit("Initial commit", author=git.Actor("Alice", "alice@example.com"))

    # Commit 2: update file1 and add file2
    file1.write_text("def run():\n    return 42\n", encoding="utf-8")
    file2 = repo_dir / "controller.py"
    file2.write_text("import service\n", encoding="utf-8")
    repo.index.add(["service.py", "controller.py"])
    repo.index.commit("Add controller", author=git.Actor("Bob", "bob@example.com"))

    analyzer = GitHistoryAnalyzer()
    res = analyzer.analyze_repository(repo)

    assert res.total_commits == 2
    assert res.total_authors == 2
    assert "service.py" in res.file_churns
    assert res.file_churns["service.py"].commit_count == 2
    assert res.file_churns["service.py"].author_count == 2
    # Verify privacy pseudonymization
    for commit in res.commits:
        assert "@" not in commit.author_alias
        assert "Contributor-" in commit.author_alias


def test_hotspot_engine_scoring():
    fixture_dir = Path("fixtures/python_project")
    structure = language_detector.scan_repository(fixture_dir)

    analysis_results = []
    for f in structure.files:
        content = Path(f.path).read_bytes()
        res = analyzer_registry.analyze_file(f.path, content, f.relative_path)
        if res:
            analysis_results.append(res)

    g = code_graph_builder.build_graph("python_project", analysis_results)
    graph_algorithms.compute_metrics(g)

    # Mock churn where database.py and user_service.py are heavily modified
    mock_churns = {
        "app/db/database.py": FileChurnMetric(
            file_path="app/db/database.py",
            commit_count=25,
            lines_added=300,
            lines_deleted=100,
            total_churn=400,
            author_count=3,
        ),
        "app/services/user_service.py": FileChurnMetric(
            file_path="app/services/user_service.py",
            commit_count=15,
            lines_added=150,
            lines_deleted=50,
            total_churn=200,
            author_count=2,
        ),
    }

    engine = HotspotEngine()
    hotspots = engine.calculate_hotspots(g, mock_churns)

    assert len(hotspots) > 0
    # database.py should have high score due to high fan-in + high churn
    top = hotspots[0]
    assert "database.py" in top.file_path or "user_service.py" in top.file_path
    assert top.score > 0
    assert "High Risk" in top.rationale
