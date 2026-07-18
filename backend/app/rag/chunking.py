"""Simple token-approx chunking (~500 tokens, 50 overlap)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int
    index: int


def _approx_tokens(text: str) -> int:
    # Rough English/INR narration heuristic: ~0.75 words per token.
    return max(1, int(len(text.split()) / 0.75))


def chunk_text(
    text: str,
    *,
    page: int = 1,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    words = (text or "").split()
    if not words:
        return []

    # Convert token budgets to word windows.
    window = max(1, int(max_tokens * 0.75))
    overlap = max(0, int(overlap_tokens * 0.75))
    step = max(1, window - overlap)

    chunks: list[Chunk] = []
    idx = 0
    start = 0
    while start < len(words):
        end = min(len(words), start + window)
        piece = " ".join(words[start:end]).strip()
        if piece:
            chunks.append(Chunk(text=piece, page=page, index=idx))
            idx += 1
        if end >= len(words):
            break
        start += step
    return chunks


def chunk_pages(pages: list[str], *, max_tokens: int = 500, overlap_tokens: int = 50) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    global_idx = 0
    for page_no, page_text in enumerate(pages, start=1):
        for ch in chunk_text(
            page_text, page=page_no, max_tokens=max_tokens, overlap_tokens=overlap_tokens
        ):
            all_chunks.append(Chunk(text=ch.text, page=ch.page, index=global_idx))
            global_idx += 1
    return all_chunks
