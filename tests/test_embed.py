"""
Tests for POST /embed endpoint.
"""

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

import app.main as main_mod
from app.main import app


class DummyEmbedder:
    async def embed(self, text: str = "", images=None):
        return np.array([0.1, 0.2, 0.3], dtype=np.float32)

    @property
    def is_loaded(self) -> bool:
        return True

    @property
    def device_name(self) -> str:
        return "cpu"


@pytest.fixture(autouse=True)
def patch_embedder():
    main_mod.embedding_service = DummyEmbedder()
    yield
    main_mod.embedding_service = None


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
    assert data["embedding"] == [0.1, 0.2, 0.3]
