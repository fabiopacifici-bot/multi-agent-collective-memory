"""
FastAPI application entry point.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.embedding import EmbeddingService

logger = logging.getLogger(__name__)

# Global state
embedding_service: EmbeddingService | None = None
write_lock = asyncio.Lock()


def get_embedder() -> EmbeddingService:
    """Return the global embedding service instance."""
    if embedding_service is None:
        raise RuntimeError("Embedding service not initialized")
    return embedding_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: load model and init DB on startup, cleanup on shutdown."""
    global embedding_service

    # Startup
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger.info("Starting Shared Memory Service ...")

    init_db()
    logger.info("Database initialized ✓")

    embedder = EmbeddingService()
    await embedder.load()
    embedding_service = embedder

    logger.info("Service ready on 0.0.0.0:8000")
    yield

    # Shutdown
    logger.info("Shutting down ...")
    embedding_service = None


app = FastAPI(
    title="Multi-Agent Shared Memory Service",
    description="Multimodal RAG shared memory over the network. "
                "Store and retrieve memories with semantic search via Qwen3-VL-Embedding-2B.",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Routes ──
from app.routers import health

app.include_router(health.router)
