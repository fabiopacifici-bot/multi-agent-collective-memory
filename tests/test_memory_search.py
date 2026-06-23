"""
Tests for GET /memory/search endpoint.
"""

import json

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_connection, init_db
from app.main import app


@pytest.fixture(autouse=True)
def setup_env():
    """Seed DB records for search tests."""
    init_db()
    conn = get_connection()
    conn.executescript("DELETE FROM memories;")

    rows = [
        ("a1", "k-alpha", "alpha memory", np.array([1.0, 0.0, 0.0], dtype=np.float32)),
        ("a2", "k-beta", "beta memory", np.array([0.0, 1.0, 0.0], dtype=np.float32)),
        ("a3", "k-gamma", "gamma memory", np.array([0.0, 0.0, 1.0], dtype=np.float32)),
    ]
    for agent, key, text, emb in rows:
        conn.execute(
            """
            INSERT INTO memories (agent, key, content_text, content_images, embedding, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (agent, key, text, json.dumps([]), emb.tobytes(), json.dumps({"seed": True})),
        )
    conn.commit()
    conn.close()

    yield


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_search_returns_ranked_top_k(client):
    """Search should return most similar memories first and respect top_k."""
    resp = await client.get("/memory/search?q=alpha&top_k=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["key"] == "k-alpha"
    assert data[0]["score"] >= data[1]["score"]


@pytest.mark.asyncio
async def test_search_requires_query(client):
    """Search without q should fail validation."""
    resp = await client.get("/memory/search")
    assert resp.status_code == 422
