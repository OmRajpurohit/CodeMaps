from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.ai.dossier import evidence_dossier_builder
from backend.app.ai.provider import get_llm_client
from backend.app.db.session import get_db

router = APIRouter()


class ExplainRequest(BaseModel):
    run_id: str = Field(..., description="UUID of the analysis run")
    file_path: str = Field(..., description="Target file path to explain")
    question: str = Field("Why is this module risky and what are the architectural concerns?", description="User query")


class ExplainResponse(BaseModel):
    file_path: str
    explanation: str
    dossier: dict[str, Any]


@router.post("/explain", response_model=ExplainResponse, summary="Get evidence-grounded AI explanation")
async def explain_module(
    req: ExplainRequest,
    db: AsyncSession = Depends(get_db),
) -> ExplainResponse:
    """
    Retrieves deterministic evidence dossier (metrics, churn, violations, blast radius)
    and generates an explanation grounded strictly in verified codebase facts.
    """
    dossier = await evidence_dossier_builder.build_dossier(db, req.run_id, req.file_path)
    client = get_llm_client()
    explanation = await client.generate_explanation(req.question, dossier)

    return ExplainResponse(
        file_path=req.file_path,
        explanation=explanation,
        dossier=dossier,
    )
