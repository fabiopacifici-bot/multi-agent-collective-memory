"""
Health check router.
"""

from fastapi import APIRouter

from app.main import get_embedder
from app.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint. Returns service status and model info."""
    embedder = get_embedder()
    return HealthResponse(
        status="ok",
        model_loaded=embedder.is_loaded,
        device=embedder.device_name,
    )
