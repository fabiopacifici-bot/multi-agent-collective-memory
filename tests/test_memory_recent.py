"""
Tests for GET /memory/recent endpoint.
"""

import json

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_connection, init_db
from app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    """Seed DB with multiple memories across agents."""
    init_db()
    conn = get_connection()
    conn.executescript("DELETE FROM memories;")

    items = [
        ("agent-a", "k-1", "first"),
        ("agent-b", "k-2", "second"),
        ("agent-a", "k-3", "third"),
    ]
    emb = np.array([1.0, 0.0, 0.0], dtype=np.float32).tobytes()
    for agent, key, text in items:
        conn.execute(
            """
            INSERT INTO memories (agent, key, content_text, content_images, embedding, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (agent, key, text, json.dumps([]), emb, json.dumps({"seed": True})),
        )
    conn.commit()
    conn.close()


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_recent_default_limit(client):
    """GET /memory/recent returns recent memories with default limit."""
    resp = await client.get("/memory/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["key"] == "k-3"


@pytest.mark.asyncio
async def test_recent_with_limit_and_agent_filter(client):
    """GET /memory/recent supports limit and agent filter."""
    resp = await client.get("/memory/recent?limit=1&agent=agent-a")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["agent"] == "agent-a"
    assert data[0]["key"] == "k-3"
