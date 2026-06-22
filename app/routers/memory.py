"""
Memory CRUD router.
"""

from __future__ import annotations

import json
import logging
import numpy as np

from fastapi import APIRouter, HTTPException, status

from app.database import get_connection
from app.main import get_embedder, write_lock
from app.models import MemoryCreate, MemoryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


def _row_to_response(row) -> MemoryResponse:
    """Convert a sqlite3.Row to a MemoryResponse."""
    return MemoryResponse(
        id=row["id"],
        agent=row["agent"],
        key=row["key"],
        content_text=row["content_text"],
        content_images=json.loads(row["content_images"]),
        metadata=json.loads(row["metadata"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(body: MemoryCreate):
    """Create a new memory with multimodal embedding.

    Generates an embedding from the provided text and/or images,
    then stores the record in the database.
    """
    embedder = get_embedder()

    # Generate embedding
    embedding = await embedder.embed(
        text=body.content.text,
        images=body.content.images if body.content.images else None,
    )

    async with write_lock:
        conn = get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO memories (agent, key, content_text, content_images, embedding, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    body.agent,
                    body.key,
                    body.content.text,
                    json.dumps(body.content.images),
                    embedding.tobytes(),
                    json.dumps(body.metadata),
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        except Exception as e:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate key or constraint violation: {e}",
            ) from e
        finally:
            conn.close()

    logger.info("Memory created: agent=%s key=%s id=%d", body.agent, body.key, row["id"])
    return _row_to_response(row)
