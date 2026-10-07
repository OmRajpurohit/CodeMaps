from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import FileNode, GitFileChurn, Hotspot, Violation


class EvidenceDossierBuilder:
    """Assembles deterministic evidence for grounded AI explanations."""

    async def build_dossier(
        self,
        db: AsyncSession,
        run_id: str,
        file_path: str,
    ) -> dict[str, Any]:
        norm_path = file_path.replace("\\", "/")

        # 1. Fetch FileNode
        fn_stmt = (
            select(FileNode)
            .where(FileNode.analysis_run_id == run_id)
            .where((FileNode.path == norm_path) | (FileNode.path.ilike(f"%{norm_path}%")))
            .limit(1)
        )
        fn_res = await db.execute(fn_stmt)
        file_node = fn_res.scalars().first()

        metrics = {}
        if file_node:
            metrics = {
                "loc": file_node.loc,
                "cyclomatic_complexity": file_node.cyclomatic_complexity,
                "fan_in": file_node.afferent_coupling,
                "fan_out": file_node.efferent_coupling,
                "instability": file_node.instability,
                "language": file_node.language,
            }

        # 2. Fetch Hotspots
        h_stmt = (
            select(Hotspot)
            .where(Hotspot.analysis_run_id == run_id)
            .where(Hotspot.file_path.ilike(f"%{norm_path}%"))
        )
        h_res = await db.execute(h_stmt)
        hotspots = [
            {"score": h.score, "rationale": h.rationale}
            for h in h_res.scalars().all()
        ]

        # 3. Fetch Violations
        v_stmt = (
            select(Violation)
            .where(Violation.analysis_run_id == run_id)
            .where(
                (Violation.source_file_path.ilike(f"%{norm_path}%"))
                | (Violation.target_file_path.ilike(f"%{norm_path}%"))
            )
        )
        v_res = await db.execute(v_stmt)
        violations = [
            {
                "rule_name": v.rule_name,
                "severity": v.severity,
                "message": v.message,
                "source": v.source_file_path,
                "target": v.target_file_path,
            }
            for v in v_res.scalars().all()
        ]

        # 4. Fetch Churn
        churn_stmt = (
            select(GitFileChurn)
            .where(GitFileChurn.analysis_run_id == run_id)
            .where((GitFileChurn.file_path == norm_path) | (GitFileChurn.file_path.ilike(f"%{norm_path}%")))
            .limit(1)
        )
        churn_res = await db.execute(churn_stmt)
        churn_obj = churn_res.scalars().first()
        churn_info = {}
        if churn_obj:
            churn_info = {
                "commit_count": churn_obj.commit_count,
                "lines_added": churn_obj.lines_added,
                "lines_deleted": churn_obj.lines_deleted,
                "author_count": churn_obj.author_count,
            }

        return {
            "run_id": run_id,
            "file_path": norm_path,
            "metrics": metrics,
            "hotspots": hotspots,
            "violations": violations,
            "churn": churn_info,
        }


evidence_dossier_builder = EvidenceDossierBuilder()
