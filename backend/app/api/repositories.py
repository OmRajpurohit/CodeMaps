
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import SecurityError, validate_repo_url
from backend.app.db.session import get_db
from backend.app.models import AnalysisRun, Repository
from backend.app.schemas import (
    AnalysisRunResponse,
    AnalysisTriggerRequest,
    RepositoryCreate,
    RepositoryResponse,
)
from backend.app.workers.orchestrator import analysis_orchestrator

router = APIRouter()


@router.post(
    "",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new repository",
)
async def register_repository(
    repo_in: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
) -> Repository:
    """Validates the repository URL and registers it in CodeAtlas."""
    try:
        clean_url = validate_repo_url(repo_in.url)
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security violation in repository URL: {str(e)}",
        )

    # Check for existing repository with same URL
    stmt = select(Repository).where(Repository.url == clean_url)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Derive repository name from URL if not specified
    derived_name = repo_in.name
    if not derived_name:
        parts = clean_url.rstrip("/").split("/")
        derived_name = parts[-1].removesuffix(".git") or "unnamed-repo"

    repo = Repository(
        url=clean_url,
        name=derived_name,
        default_branch=repo_in.default_branch,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    return repo


@router.get(
    "",
    response_model=list[RepositoryResponse],
    summary="List all registered repositories",
)
async def list_repositories(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[Repository]:
    """Retrieves all registered repositories ordered by creation date."""
    stmt = (
        select(Repository)
        .order_by(Repository.created_at.desc())
        .offset(skip)
        .limit(min(limit, 100))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{repo_id}",
    response_model=RepositoryResponse,
    summary="Get repository details",
)
async def get_repository(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
) -> Repository:
    """Retrieves a single repository by UUID."""
    stmt = select(Repository).where(Repository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID '{repo_id}' not found.",
        )
    return repo


@router.post(
    "/{repo_id}/analyze",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger repository analysis run",
)
async def trigger_analysis(
    repo_id: str,
    trigger_req: AnalysisTriggerRequest = AnalysisTriggerRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
) -> AnalysisRun:
    """Triggers an asynchronous analysis run for the repository."""
    stmt = select(Repository).where(Repository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID '{repo_id}' not found.",
        )

    # Create new queued analysis run
    run = AnalysisRun(
        repository_id=repo.id,
        commit_sha=trigger_req.branch or "HEAD",
        status="QUEUED",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Enqueue background task
    background_tasks.add_task(analysis_orchestrator.execute_run, run.id)

    return run


@router.get(
    "/{repo_id}/status",
    summary="Get latest repository analysis run status",
)
async def get_repository_status(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves the status of the most recent analysis run for this repository."""
    stmt = (
        select(AnalysisRun)
        .where(AnalysisRun.repository_id == repo_id)
        .order_by(AnalysisRun.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    latest_run = result.scalar_one_or_none()
    if not latest_run:
        return {"status": "NOT_ANALYZED", "run_id": None}

    return {
        "run_id": latest_run.id,
        "status": latest_run.status,
        "commit_sha": latest_run.commit_sha,
        "error_message": latest_run.error_message,
        "summary_stats": latest_run.summary_stats,
        "started_at": latest_run.started_at,
        "completed_at": latest_run.completed_at,
    }


@router.delete(
    "/{repo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete repository",
)
async def delete_repository(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deletes repository and all associated analysis runs and graph data."""
    stmt = select(Repository).where(Repository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID '{repo_id}' not found.",
        )
    await db.delete(repo)
    await db.commit()
