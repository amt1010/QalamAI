from fastapi import APIRouter

from app.models.inscription import AnalyzeRequest, AnalyzeResponse
from app.services.pipeline import InferencePipeline

router = APIRouter(prefix="/api/v1", tags=["inscriptions"])
pipeline = InferencePipeline()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_inscription(request: AnalyzeRequest) -> AnalyzeResponse:
    return pipeline.run(request)
