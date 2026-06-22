"""
Pydantic models for request/response schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class Content(BaseModel):
    """Multimodal content: text + optional base64-encoded images."""
    text: str = ""
    images: list[str] = Field(default_factory=list)


class MemoryCreate(BaseModel):
    """Request body for POST /memory."""
    agent: str = Field(..., min_length=1, description="Agent identifier")
    key: str = Field(..., min_length=1, description="Logical key for the memory")
    content: Content = Field(default_factory=Content)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    """Request body for PUT /memory/{key}."""
    content: Content = Field(default_factory=Content)
    metadata: dict[str, Any] | None = None


class MemoryResponse(BaseModel):
    """Response body for a single memory record."""
    id: int
    agent: str
    key: str
    content_text: str
    content_images: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmbedRequest(BaseModel):
    """Request body for POST /embed (debug endpoint)."""
    text: str = ""
    images: list[str] = Field(default_factory=list)


class EmbedResponse(BaseModel):
    """Response body for POST /embed."""
    embedding: list[float]
    dim: int


class SearchResult(BaseModel):
    """A single search result with similarity score."""
    id: int
    agent: str
    key: str
    content_text: str
    content_images: list[str]
    metadata: dict[str, Any]
    score: float
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    """Response body for GET /health."""
    status: str
    model_loaded: bool
    device: str
