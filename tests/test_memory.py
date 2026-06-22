"""
Tests for the memory CRUD endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_create_memory(client):
    """POST /memory should create a memory and return 201."""
    payload = {
        "agent": "millie",
        "key": "test-key-1",
        "content": {
            "text": "Hello from Millie",
        },
        "metadata": {"source": "test"},
    }
    resp = await client.post("/memory", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["agent"] == "millie"
    assert data["key"] == "test-key-1"
    assert data["content_text"] == "Hello from Millie"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_memory_duplicate_key(client):
    """POST /memory with duplicate key should return 409."""
    payload = {
        "agent": "millie",
        "key": "dup-key",
        "content": {"text": "first"},
    }
    resp1 = await client.post("/memory", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/memory", json=payload)
    assert resp2.status_code == 409
