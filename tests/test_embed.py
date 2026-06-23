"""Tests for POST /embed endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_post_embed_returns_vector_and_dim(client):
    resp = await client.post("/embed", json={"text": "hello", "images": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["dim"] == 3
    assert isinstance(data["embedding"], list)
    assert len(data["embedding"]) == 3
