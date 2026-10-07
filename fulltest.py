import asyncio
from pathlib import Path
from backend.app.models import AnalysisRun, Repository
from backend.app.db.session import AsyncSessionLocal
from backend.app.workers.orchestrator import analysis_orchestrator
from sqlalchemy import select

# Replace with your repository URL or local folder path
REPO_URL = "https://github.com/OmRajpurohit/movie-recommender"
REPO_NAME = "movie_recommender"


async def run_full_test():
    async with AsyncSessionLocal() as db:
        # 1. Register / fetch repository
        stmt = select(Repository).where(Repository.url == REPO_URL)
        res = await db.execute(stmt)
        repo = res.scalar_one_or_none()
        if not repo:
            repo = Repository(url=REPO_URL, name=REPO_NAME, default_branch="main")
            db.add(repo)
            await db.commit()
            await db.refresh(repo)

        print(f"[*] Repository ready: {repo.name} ({repo.id})")

        # 2. Create queued analysis run
        run = AnalysisRun(repository_id=repo.id, commit_sha="HEAD", status="QUEUED")
        db.add(run)
        await db.commit()
        await db.refresh(run)
        print(f"[*] Created analysis run: {run.id}")

    # 3. Execute full pipeline
    print("[*] Starting analysis pipeline...")
    await analysis_orchestrator.execute_run(run.id)

    # 4. Check results
    async with AsyncSessionLocal() as db:
        stmt = select(AnalysisRun).where(AnalysisRun.id == run.id)
        res = await db.execute(stmt)
        completed_run = res.scalar_one_or_none()
        print("=" * 60)
        print(f"Analysis Status : {completed_run.status}")
        print(f"Summary Stats   : {completed_run.summary_stats}")
        if completed_run.error_message:
            print(f"Error           : {completed_run.error_message}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_full_test())