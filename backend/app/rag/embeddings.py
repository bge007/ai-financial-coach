"""Local embedding adapter (FastEmbed). Tests inject a FakeEmbedder."""

from __future__ import annotations

import hashlib
import math
from typing import Protocol

from app.core.config import get_settings


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    @property
    def dim(self) -> int: ...


class FakeEmbedder:
    """Deterministic hash embeddings for unit tests (no model download)."""

    def __init__(self, dim: int = 384):
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vals = []
            i = 0
            while len(vals) < self._dim:
                b = digest[i % len(digest)]
                vals.append((b / 255.0) * 2 - 1)
                i += 1
            # L2-normalize
            norm = math.sqrt(sum(v * v for v in vals)) or 1.0
            out.append([v / norm for v in vals])
        return out


class FastEmbedder:
    def __init__(self, model_name: str | None = None, dim: int | None = None):
        from fastembed import TextEmbedding

        settings = get_settings()
        self._model_name = model_name or settings.embedding_model
        self._dim = dim or settings.embedding_dim
        self._model = TextEmbedding(model_name=self._model_name)

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = list(self._model.embed(texts))
        return [list(map(float, v)) for v in vectors]


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        settings = get_settings()
        if settings.environment == "test":
            _embedder = FakeEmbedder(dim=settings.embedding_dim)
        else:
            try:
                _embedder = FastEmbedder()
            except Exception:
                # Fallback when model can't download (offline/dev).
                _embedder = FakeEmbedder(dim=settings.embedding_dim)
    return _embedder


def set_embedder(embedder: Embedder | None) -> None:
    global _embedder
    _embedder = embedder
