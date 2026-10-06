import networkx as nx
from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.diff.analyzer import architecture_diff_analyzer

router = APIRouter()


class ArchitectureDiffRequest(BaseModel):
    base_commit: str = "HEAD~1"
    target_commit: str = "HEAD"


@router.post("", summary="Compare architecture between two commits")
async def compare_commits_architecture(
    diff_req: ArchitectureDiffRequest,
):
    """
    Computes architectural diff between two commits: added/removed dependencies,
    new cycles, and coupling risk score.
    """
    # For now, stub graphs or diff analyzer dispatch
    g_base = nx.MultiDiGraph()
    g_target = nx.MultiDiGraph()

    diff_res = architecture_diff_analyzer.diff_graphs(
        g_base, g_target, diff_req.base_commit, diff_req.target_commit
    )
    return diff_res
