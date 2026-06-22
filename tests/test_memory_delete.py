"""
Tests for DELETE /memory/{key} endpoint.
"""

import json

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_connection, init_db
from app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    """Seed DB with one deletable memory."""
    init_db()
    conn = get_connection()
    conn.executescript("DELETE FROM memories;")
    conn.execute(
        """
        INSERT INTO memories (agent, key, content_text, content_images, embedding, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "agent-del",
            "del-key",
            "to be deleted",
            json.dumps([]),
            np.array([1.0, 0.0, 0.0], dtype=np.float32).tobytes(),
            json.dumps({"seed": True}),
        ),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_delete_memory_success(client):
    """DELETE /memory/{key} removes existing memory."""
    resp = await client.delete("/memory/del-key")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is True
    assert data["key"] == "del-key"

    check = await client.get("/memory/key/del-key")
    assert check.status_code == 404


@pytest.mark.asyncio
async def test_delete_memory_not_found(client):
    """DELETE /memory/{key} returns 404 when key is missing."""
    resp = await client.delete("/memory/not-found")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Memory not found"
