"""
Tests for PUT /memory/{key} endpoint.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_connection, init_db
from app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    """Ensure test records exist and DB is clean enough for PUT tests."""
    init_db()
    conn = get_connection()
    conn.executescript("DELETE FROM memories;")
    conn.execute(
        """
        INSERT INTO memories (agent, key, content_text, content_images, embedding, metadata)
        VALUES ('millie', 'put-key', 'old text', '[]', X'00', '{"source":"seed"}')
        """
    )
    conn.commit()
    conn.close()


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_put_memory_updates_existing_key(client):
    """PUT /memory/{key} should update content and metadata for existing key."""
    payload = {
        "content": {
            "text": "updated text",
            "images": [],
        },
        "metadata": {"source": "updated"},
    }

    resp = await client.put("/memory/put-key", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "put-key"
    assert data["content_text"] == "updated text"
    assert data["metadata"]["source"] == "updated"


@pytest.mark.asyncio
async def test_put_memory_not_found(client):
    """PUT /memory/{key} should return 404 if key does not exist."""
    payload = {
        "content": {
            "text": "new text",
            "images": [],
        }
    }

    resp = await client.put("/memory/missing-key", json=payload)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Memory not found"
