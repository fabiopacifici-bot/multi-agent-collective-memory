"""
Embedding service wrapping Qwen3-VL-Embedding-2B.
Loaded once at startup via FastAPI lifespan.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

logger = logging.getLogger(__name__)

# Will be populated at runtime when the model is loaded
_embedder = None
_device = "cpu"


class EmbeddingService:
    """Thin wrapper around the Qwen3-VL-Embedding-2B model."""

    def __init__(self, model_name: str = "Qwen/Qwen3-VL-Embedding-2B"):
        self.model_name = model_name
        self.model = None
        self.processor = None
        self.device = "cpu"

    async def load(self) -> None:
        """Load the model and processor. Called once at startup."""
        import torch
        from transformers import AutoModel, AutoProcessor

        logger.info("Loading embedding model: %s ...", self.model_name)

        if torch.cuda.is_available():
            self.device = "cuda"
            logger.info("CUDA available — loading model on GPU")
        else:
            self.device = "cpu"
            logger.info("CUDA not available — falling back to CPU")

        self.processor = AutoProcessor.from_pretrained(
            self.model_name, trust_remote_code=True
        )
        self.model = AutoModel.from_pretrained(
            self.model_name, trust_remote_code=True
        ).to(self.device)
        self.model.eval()

        logger.info("Embedding model loaded on %s ✓", self.device)

    async def embed(
        self,
        text: str = "",
        images: list[str] | None = None,
    ) -> np.ndarray:
        """Generate an embedding vector for the given text and/or images.

        Args:
            text: Input text string.
            images: Optional list of base64-encoded image strings.

        Returns:
            numpy array of shape (1024,) with the embedding.
        """
        if self.model is None or self.processor is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        import torch

        # Build multimodal input
        messages = []
        content_parts = []

        if images:
            for img_b64 in images:
                content_parts.append({"type": "image", "image": f"data:image/png;base64,{img_b64}"})

        if text:
            content_parts.append({"type": "text", "text": text})

        messages.append({"role": "user", "content": content_parts})

        # Process with Qwen VL processor
        inputs = self.processor(
            text=[self.processor.apply_chat_template(messages)],
            padding=True,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            output = self.model(**inputs)

        # Extract embedding from the last hidden state (pooling)
        # Qwen3-VL-Embedding uses mean pooling over the last hidden state
        last_hidden = output.last_hidden_state  # (1, seq_len, hidden_dim)
        attention_mask = inputs.get("attention_mask")
        if attention_mask is not None:
            mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
            embedding = (last_hidden * mask_expanded).sum(dim=1) / mask_expanded.sum(dim=1).clamp(min=1e-9)
        else:
            embedding = last_hidden.mean(dim=1)

        # Normalize to unit length
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        return embedding.squeeze(0).cpu().numpy().astype(np.float32)

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    @property
    def device_name(self) -> str:
        return self.device
