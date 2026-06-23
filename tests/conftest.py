"""Shared test configuration and global fixtures."""

from __future__ import annotations

import json

import numpy as np
import pytest

import app.main as main_mod
from app.database import get_connection, init_db


class DummyEmbedder:
    """Fast deterministic embedder for test environment."""

    async def embed(self, text: str = "", images=None):
        if text == "alpha":
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if text == "beta":
            return np.array([0.0, 1.0, 0.0], dtype=np.float32)
        return np.array([0.0, 0.0, 1.0], dtype=np.float32)

    @property
    def is_loaded(self) -> bool:
        return True

    @property
    def device_name(self) -> str:
        return "cpu"


@pytest.fixture(autouse=True)
def patch_global_embedder():
    """Avoid loading real HF model during tests."""
    main_mod.embedding_service = DummyEmbedder()
    yield
    main_mod.embedding_service = None


@pytest.fixture(autouse=True)
def init_test_db():
    """Ensure table exists for each test module execution context."""
    init_db()


@pytest.fixture
def seed_single_memory():
    """Utility fixture for tests that need one default memory row."""
    conn = get_connection()
    conn.executescript("DELETE FROM memories;")
    conn.execute(
        """
        INSERT INTO memories (agent, key, content_text, content_images, embedding, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "test-agent",
            "test-key",
            "hello world",
            json.dumps([]),
            np.array([1.0, 0.0, 0.0], dtype=np.float32).tobytes(),
            json.dumps({"env": "test"}),
        ),
    )
    conn.commit()
    conn.close()
