"""Qdrant store wrapper — every query MUST filter by user_id."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.config import get_settings
from app.rag.embeddings import Embedder, get_embedder

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    score: float
    source_file: str
    page: int
    user_id: int


class DocumentStore:
    def __init__(
        self,
        client: QdrantClient | None = None,
        embedder: Embedder | None = None,
        collection: str | None = None,
    ):
        settings = get_settings()
        self.collection = collection or settings.qdrant_collection
        self.embedder = embedder or get_embedder()
        self._available = True
        if client is not None:
            self.client = client
        elif settings.qdrant_url in {":memory:", "memory"}:
            self.client = QdrantClient(location=":memory:")
        else:
            self.client = QdrantClient(url=settings.qdrant_url)
        self._init_collection()

    def _init_collection(self) -> None:
        try:
            self._ensure_collection()
        except Exception as exc:
            settings = get_settings()
            if settings.qdrant_url in {":memory:", "memory"}:
                logger.warning("Qdrant collection init failed: %s", exc)
                self._available = False
                return
            logger.warning(
                "Qdrant unavailable at %s (%s); using in-memory fallback",
                settings.qdrant_url,
                exc,
            )
            self.client = QdrantClient(location=":memory:")
            try:
                self._ensure_collection()
            except Exception as inner:
                logger.warning("In-memory Qdrant init failed: %s", inner)
                self._available = False

    def _ensure_collection(self) -> None:
        if not self._available:
            return
        names = {c.name for c in self.client.get_collections().collections}
        if self.collection in names:
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=qm.VectorParams(
                size=self.embedder.dim,
                distance=qm.Distance.COSINE,
            ),
        )

    def upsert_chunks(
        self,
        *,
        user_id: int,
        source_file: str,
        chunks: list[tuple[str, int]],
    ) -> int:
        """Upsert (text, page) chunks for a user. Returns count upserted."""
        if not chunks or not self._available:
            return 0
        try:
            texts = [t for t, _ in chunks]
            vectors = self.embedder.embed(texts)
            points = []
            for (text, page), vector in zip(chunks, vectors, strict=True):
                points.append(
                    qm.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "user_id": user_id,
                            "source_file": source_file,
                            "page": page,
                            "text": text,
                        },
                    )
                )
            self.client.upsert(collection_name=self.collection, points=points)
            return len(points)
        except Exception as exc:
            logger.warning("Qdrant upsert failed: %s", exc)
            return 0

    def search(self, user_id: int, query: str, k: int = 6) -> list[RetrievedChunk]:
        if not self._available:
            return []
        try:
            vector = self.embedder.embed([query])[0]
            result = self.client.query_points(
                collection_name=self.collection,
                query=vector,
                limit=k,
                query_filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="user_id",
                            match=qm.MatchValue(value=user_id),
                        )
                    ]
                ),
                with_payload=True,
            )
        except Exception as exc:
            logger.warning("Qdrant search failed: %s", exc)
            return []
        out: list[RetrievedChunk] = []
        for hit in result.points:
            payload: dict[str, Any] = hit.payload or {}
            # Defense in depth — never return another user's chunk.
            if int(payload.get("user_id", -1)) != int(user_id):
                continue
            out.append(
                RetrievedChunk(
                    text=str(payload.get("text", "")),
                    score=float(hit.score or 0.0),
                    source_file=str(payload.get("source_file", "")),
                    page=int(payload.get("page") or 1),
                    user_id=int(payload["user_id"]),
                )
            )
        return out

    def delete_user(self, user_id: int) -> None:
        if not self._available:
            return
        try:
            self.client.delete(
                collection_name=self.collection,
                points_selector=qm.FilterSelector(
                    filter=qm.Filter(
                        must=[
                            qm.FieldCondition(
                                key="user_id",
                                match=qm.MatchValue(value=user_id),
                            )
                        ]
                    )
                ),
            )
        except Exception as exc:
            logger.warning("Qdrant delete_user failed: %s", exc)


_store: DocumentStore | None = None


def get_store() -> DocumentStore:
    global _store
    if _store is None:
        _store = DocumentStore()
    return _store


def set_store(store: DocumentStore | None) -> None:
    global _store
    _store = store
