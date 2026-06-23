"""
Tests for GET /memory/{id} and GET /memory/key/{key} endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_connection, init_db
from app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize a fresh in-memory database before each test."""
    init_db()
    conn = get_connection()
    conn.executescript("DELETE FROM memories; DELETE FROM sqlite_sequence WHERE name='memories';")
    conn.execute(
        """
        INSERT INTO memories (agent, key, content_text, content_images, embedding, metadata)
        VALUES ('test-agent', 'test-key', 'hello world', '[]', X'00', '{"env":"test"}')
        """,
    )
    conn.commit()
    conn.close()


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_get_memory_by_id_found(client):
    """GET /memory/{id} should return the memory when it exists."""
    resp = await client.get("/memory/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["agent"] == "test-agent"
    assert data["key"] == "test-key"
    assert data["content_text"] == "hello world"


@pytest.mark.asyncio
async def test_get_memory_by_id_not_found(client):
    """GET /memory/{id} should return 404 for non-existent ID."""
    resp = await client.get("/memory/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Memory not found"


@pytest.mark.asyncio
async def test_get_memory_by_key_found(client):
    """GET /memory/key/{key} should return the memory when it exists."""
    resp = await client.get("/memory/key/test-key")
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "test-key"
    assert data["content_text"] == "hello world"


@pytest.mark.asyncio
async def test_get_memory_by_key_not_found(client):
    """GET /memory/key/{key} should return 404 for non-existent key."""
    resp = await client.get("/memory/key/nonexistent")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Memory not found"
