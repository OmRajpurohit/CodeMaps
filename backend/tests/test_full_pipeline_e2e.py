from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import AnalysisRun
from backend.app.workers.orchestrator import analysis_orchestrator


@pytest.mark.asyncio
async def test_full_analysis_pipeline_e2e(client: AsyncClient, db_session: AsyncSession):
    # 1. Register fixture repository
    fixture_path = str(Path("fixtures/python_project").resolve())
    create_resp = await client.post(
        "/api/v1/repositories",
        json={
            "url": fixture_path,
            "name": "python_fixture_project",
            "default_branch": "main",
        },
    )
    assert create_resp.status_code == 201
    repo_data = create_resp.json()
    repo_id = repo_data["id"]

    # 2. Trigger analysis run directly through orchestrator for synchronous testing
    run = AnalysisRun(
        repository_id=repo_id,
        commit_sha="HEAD",
        status="QUEUED",
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    run_id = run.id

    # Execute the complete analysis pipeline
    from backend.tests.conftest import TestingSessionLocal
    await analysis_orchestrator.execute_run(run_id, session_factory=TestingSessionLocal)

    # Refresh run from DB to verify completion
    db_session.expire_all()
    stmt = select(AnalysisRun).where(AnalysisRun.id == run_id)
    res = await db_session.execute(stmt)
    completed_run = res.scalar_one_or_none()

    assert completed_run is not None
    assert completed_run.status == "COMPLETED"
    assert completed_run.error_message is None
    assert completed_run.summary_stats is not None
    assert completed_run.summary_stats["total_files"] >= 7
    assert completed_run.summary_stats["total_cycles"] >= 1
    assert completed_run.summary_stats["total_violations"] >= 1

    # 3. Test Overview API
    overview_resp = await client.get(f"/api/v1/runs/{run_id}/overview")
    assert overview_resp.status_code == 200
    ov_data = overview_resp.json()
    assert ov_data["status"] == "COMPLETED"
    assert ov_data["primary_language"] == "Python"
    assert ov_data["total_cycles"] >= 1

    # 4. Test Dependency Graph API
    graph_resp = await client.get(f"/api/v1/runs/{run_id}/graph")
    assert graph_resp.status_code == 200
    g_data = graph_resp.json()
    assert g_data["total_nodes"] > 10
    assert g_data["total_edges"] > 10

    # 5. Test Cycles API
    cycles_resp = await client.get(f"/api/v1/runs/{run_id}/cycles")
    assert cycles_resp.status_code == 200
    c_data = cycles_resp.json()
    assert c_data["total_cycles"] >= 1
    assert any("module_" in c["description"] for c in c_data["cycles"])

    # 6. Test Impact Analysis API
    impact_resp = await client.get(f"/api/v1/runs/{run_id}/impact?target=file:app/db/database.py")
    assert impact_resp.status_code == 200
    imp_data = impact_resp.json()
    assert imp_data["direct_dependents_count"] >= 1
    assert imp_data["impact_score"] > 0.0

    # 7. Test Violations API
    viol_resp = await client.get(f"/api/v1/runs/{run_id}/violations")
    assert viol_resp.status_code == 200
    v_data = viol_resp.json()
    assert v_data["total_violations"] >= 1
    assert any("Layer Boundary Violation" in v["rule_name"] for v in v_data["violations"])

    # 8. Test Hotspots API
    hotspot_resp = await client.get(f"/api/v1/runs/{run_id}/hotspots")
    assert hotspot_resp.status_code == 200
    h_data = hotspot_resp.json()
    assert h_data["total_hotspots"] >= 1

    # 9. Test AI Explain API
    ai_resp = await client.post(
        "/api/v1/ai/explain",
        json={
            "run_id": run_id,
            "file_path": "app/db/database.py",
            "question": "Why is database.py a high impact component?",
        },
    )
    assert ai_resp.status_code == 200
    ai_data = ai_resp.json()
    assert "Architectural Analysis" in ai_data["explanation"]
    assert "database.py" in ai_data["explanation"]
