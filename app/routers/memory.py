"""
Memory CRUD router.
"""

from __future__ import annotations

import json
import logging
import numpy as np

from fastapi import APIRouter, HTTPException, Query, status

from app.database import get_connection
from app.main import get_embedder, write_lock
from app.models import MemoryCreate, MemoryResponse, MemoryUpdate, SearchResult

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


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


@router.get("/recent", response_model=list[MemoryResponse])
async def get_recent_memories(
    limit: int = Query(10, ge=1, le=200, description="Number of most recent memories"),
    agent: str | None = Query(None, description="Optional agent filter"),
):
    """Return the most recent memories, optionally filtered by agent."""
    conn = get_connection()
    try:
        if agent:
            rows = conn.execute(
                """
                SELECT * FROM memories
                WHERE agent = ?
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT ?
                """,
                (agent, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM memories
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()

    return [_row_to_response(row) for row in rows]


@router.get("/{id:int}", response_model=MemoryResponse)
async def get_memory_by_id(id: int):
    """Retrieve a memory by its primary key ID."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (id,)).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return _row_to_response(row)


@router.get("/key/{key}", response_model=MemoryResponse)
async def get_memory_by_key(key: str):
    """Retrieve a memory by its logical key."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM memories WHERE key = ?", (key,)).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return _row_to_response(row)


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


@router.put("/{key}", response_model=MemoryResponse)
async def update_memory(key: str, body: MemoryUpdate):
    """Update an existing memory by logical key and regenerate its embedding."""
    embedder = get_embedder()

    # Regenerate embedding from the updated multimodal content.
    embedding = await embedder.embed(
        text=body.content.text,
        images=body.content.images if body.content.images else None,
    )

    async with write_lock:
        conn = get_connection()
        try:
            existing = conn.execute(
                "SELECT * FROM memories WHERE key = ?", (key,)
            ).fetchone()
            if existing is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Memory not found",
                )

            metadata_value = json.dumps(body.metadata) if body.metadata is not None else existing["metadata"]

            conn.execute(
                """
                UPDATE memories
                SET content_text = ?,
                    content_images = ?,
                    embedding = ?,
                    metadata = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE key = ?
                """,
                (
                    body.content.text,
                    json.dumps(body.content.images),
                    embedding.tobytes(),
                    metadata_value,
                    key,
                ),
            )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM memories WHERE key = ?", (key,)
            ).fetchone()
        finally:
            conn.close()

    logger.info("Memory updated: key=%s id=%d", key, row["id"])
    return _row_to_response(row)


@router.get("/search", response_model=list[SearchResult])
async def search_memories(
    q: str = Query(..., min_length=1, description="Semantic query text"),
    top_k: int = Query(5, ge=1, le=100, description="Maximum results to return"),
):
    """Search memories by semantic similarity against query text."""
    embedder = get_embedder()
    query_embedding = await embedder.embed(text=q, images=None)

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM memories WHERE embedding IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()

    ranked: list[SearchResult] = []
    for row in rows:
        raw = row["embedding"]
        if raw is None:
            continue

        emb = np.frombuffer(raw, dtype=np.float32)
        if emb.size == 0 or emb.shape != query_embedding.shape:
            continue

        score = _cosine_similarity(query_embedding, emb)
        ranked.append(
            SearchResult(
                id=row["id"],
                agent=row["agent"],
                key=row["key"],
                content_text=row["content_text"],
                content_images=json.loads(row["content_images"]),
                metadata=json.loads(row["metadata"]),
                score=score,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:top_k]


@router.delete("/{key}")
async def delete_memory(key: str):
    """Delete a memory by logical key."""
    async with write_lock:
        conn = get_connection()
        try:
            existing = conn.execute(
                "SELECT id FROM memories WHERE key = ?", (key,)
            ).fetchone()
            if existing is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Memory not found",
                )

            conn.execute("DELETE FROM memories WHERE key = ?", (key,))
            conn.commit()
        finally:
            conn.close()

    logger.info("Memory deleted: key=%s", key)
    return {"deleted": True, "key": key}
