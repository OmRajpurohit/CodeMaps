from fastapi import APIRouter

from backend.app.api import ai, diff, health, repositories, runs

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
api_router.include_router(runs.router, prefix="/runs", tags=["Analysis Runs"])
api_router.include_router(diff.router, prefix="/diff", tags=["Architecture Diff"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI Assistant"])
