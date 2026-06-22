"""
Embedding debug router.
"""

from fastapi import APIRouter

from app.main import get_embedder
from app.models import EmbedRequest, EmbedResponse

router = APIRouter(tags=["embed"])


@router.post("/embed", response_model=EmbedResponse)
async def generate_embedding(body: EmbedRequest):
    """Generate embedding from text/images without storing memory."""
    embedder = get_embedder()
    vector = await embedder.embed(
        text=body.text,
        images=body.images if body.images else None,
    )
    return EmbedResponse(embedding=vector.tolist(), dim=int(vector.shape[0]))
