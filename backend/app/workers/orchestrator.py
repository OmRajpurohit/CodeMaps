import shutil
from datetime import UTC, datetime
from pathlib import Path

import git
from sqlalchemy import select

from backend.app.analyzers.registry import analyzer_registry
from backend.app.core.logging import logger
from backend.app.db.session import AsyncSessionLocal
from backend.app.git.analyzer import git_history_analyzer
from backend.app.graph.algorithms import graph_algorithms
from backend.app.graph.builder import code_graph_builder
from backend.app.graph.persistence import graph_persistence_service
from backend.app.hotspots.engine import hotspot_engine
from backend.app.ingestion.cloner import git_cloner
from backend.app.ingestion.detector import language_detector
from backend.app.ingestion.sandbox import sandbox_manager
from backend.app.models import (
    AnalysisRun,
    GitCommit,
    GitFileChurn,
    Hotspot,
    Repository,
    Violation,
)
from backend.app.rules.engine import architecture_rule_engine


class AnalysisOrchestrator:
    """
    Orchestrates the entire asynchronous repository intelligence pipeline:
    Clone -> Detect -> AST Parse -> Graph Build -> Graph Metrics -> Git History -> Hotspots -> Rules -> Persist.
    """

    def __init__(self, session_factory=None) -> None:
        self.session_factory = session_factory or AsyncSessionLocal

    async def execute_run(self, analysis_run_id: str, session_factory=None) -> None:
        logger.info("Starting analysis run execution for ID %s...", analysis_run_id)
        sandbox_path: Path | None = None
        factory = session_factory or self.session_factory

        async with factory() as db:
            # 1. Fetch AnalysisRun & Repository
            stmt = select(AnalysisRun).where(AnalysisRun.id == analysis_run_id)
            result = await db.execute(stmt)
            run = result.scalar_one_or_none()
            if not run:
                logger.error("Analysis run with ID %s not found.", analysis_run_id)
                return

            repo_stmt = select(Repository).where(Repository.id == run.repository_id)
            repo_res = await db.execute(repo_stmt)
            repo = repo_res.scalar_one_or_none()
            if not repo:
                logger.error("Parent repository for run %s not found.", analysis_run_id)
                return

            try:
                run.status = "CLONING"
                run.started_at = datetime.now(UTC)
                await db.commit()

                # 2. Setup Sandbox
                sandbox_path = sandbox_manager.create_sandbox(prefix=f"run_{analysis_run_id[:8]}")

                # 3. Clone or copy local repository
                repo_dir = sandbox_path / "repo"
                is_local = Path(repo.url).exists()

                if is_local:
                    # For local file paths or fixtures
                    logger.info("Copying local repository from %s...", repo.url)
                    shutil.copytree(
                        repo.url,
                        repo_dir,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules", ".venv"),
                    )
                    # Initialize git if not present so git analyzer works
                    try:
                        git_repo = git.Repo(repo_dir)
                    except Exception:
                        git_repo = git.Repo.init(repo_dir)
                        git_repo.index.add("*")
                        git_repo.index.commit("Local analysis snapshot")
                else:
                    git_repo = git_cloner.clone(
                        repo_url=repo.url,
                        target_dir=repo_dir,
                        branch=repo.default_branch if repo.default_branch != "main" else None,
                    )

                # 4. Extract Commit Metadata
                metadata = git_cloner.extract_metadata(git_repo)
                run.commit_sha = metadata.commit_sha

                # 5. Language Detection & File Indexing
                run.status = "SCANNING"
                await db.commit()

                structure = language_detector.scan_repository(repo_dir)
                repo.primary_language = structure.primary_language

                # 6. AST Parsing
                run.status = "PARSING"
                await db.commit()

                analysis_results = []
                for f in structure.files:
                    try:
                        content = Path(f.path).read_bytes()
                        res = analyzer_registry.analyze_file(f.path, content, f.relative_path)
                        if res:
                            analysis_results.append(res)
                    except Exception as parse_err:
                        logger.warning("Failed to parse file %s: %s", f.relative_path, str(parse_err))

                # 7. Construct Knowledge Graph
                run.status = "GRAPH_BUILDING"
                await db.commit()

                g = code_graph_builder.build_graph(repo.name, analysis_results)

                # 8. Compute Graph Metrics & Cycle Detection
                graph_algorithms.compute_metrics(g)
                cycles = graph_algorithms.detect_cycles(g)
                sccs = graph_algorithms.detect_scc(g)

                # 9. Git History Analysis
                run.status = "GIT_ANALYZING"
                await db.commit()

                git_results = git_history_analyzer.analyze_repository(git_repo)

                # 10. Hotspot Scoring
                hotspots = hotspot_engine.calculate_hotspots(g, git_results.file_churns)

                # 11. Architecture Rule Evaluation
                run.status = "EVALUATING_RULES"
                await db.commit()

                violations = architecture_rule_engine.evaluate_architecture(g)

                # 12. Batch Persistence to Database
                run.status = "PERSISTING"
                await db.commit()

                # Persist FileNodes, Symbols, and GraphEdges
                await graph_persistence_service.persist_graph(db, run.id, g)

                # Persist Git Commits
                for c in git_results.commits[:100]:
                    db.add(
                        GitCommit(
                            analysis_run_id=run.id,
                            commit_sha=c.commit_sha,
                            author_alias=c.author_alias,
                            authored_at=c.authored_at,
                            message=c.message,
                            insertions=c.insertions,
                            deletions=c.deletions,
                            files_changed=c.files_changed,
                        )
                    )

                # Persist File Churns
                for fc in git_results.file_churns.values():
                    db.add(
                        GitFileChurn(
                            analysis_run_id=run.id,
                            file_path=fc.file_path,
                            commit_count=fc.commit_count,
                            lines_added=fc.lines_added,
                            lines_deleted=fc.lines_deleted,
                            author_count=fc.author_count,
                            ownership_entropy=fc.ownership_hhi,
                        )
                    )

                # Persist Hotspots
                for h in hotspots[:50]:
                    db.add(
                        Hotspot(
                            analysis_run_id=run.id,
                            file_path=h.file_path,
                            score=h.score,
                            churn_score=h.churn_score,
                            centrality_score=h.centrality_score,
                            complexity_score=h.complexity_score,
                            rationale=h.rationale,
                        )
                    )

                # Persist Violations
                for v in violations:
                    db.add(
                        Violation(
                            analysis_run_id=run.id,
                            source_file_path=v.source_file_path,
                            target_file_path=v.target_file_path,
                            rule_name=v.rule_name,
                            severity=v.severity,
                            message=v.message,
                            layer_from=v.layer_from,
                            layer_to=v.layer_to,
                        )
                    )

                # Calculate Architecture Health Score (0 - 100)
                error_violations = sum(1 for v in violations if v.severity == "error")
                warning_violations = sum(1 for v in violations if v.severity == "warning")
                health_deduction = len(cycles) * 15.0 + error_violations * 10.0 + warning_violations * 3.0
                health_score = round(max(0.0, 100.0 - health_deduction), 1)

                run.summary_stats = {
                    "total_files": structure.total_files,
                    "total_loc": structure.total_loc,
                    "primary_language": structure.primary_language,
                    "languages_breakdown": structure.languages,
                    "total_nodes": g.number_of_nodes(),
                    "total_edges": g.number_of_edges(),
                    "total_cycles": len(cycles),
                    "total_sccs": len(sccs),
                    "total_violations": len(violations),
                    "total_hotspots": len(hotspots),
                    "total_commits": git_results.total_commits,
                    "health_score": health_score,
                }

                run.status = "COMPLETED"
                run.completed_at = datetime.now(UTC)
                await db.commit()
                logger.info(
                    "Analysis run %s completed successfully. Health Score: %.1f",
                    run.id,
                    health_score,
                )

            except Exception as e:
                logger.exception("Analysis run %s failed: %s", analysis_run_id, str(e))
                run.status = "FAILED"
                run.error_message = str(e)
                run.completed_at = datetime.now(UTC)
                await db.commit()

            finally:
                if sandbox_path:
                    sandbox_manager.cleanup_sandbox(sandbox_path)


analysis_orchestrator = AnalysisOrchestrator()
