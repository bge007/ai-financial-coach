"""Simple in-memory rate limiter for auth/upload/ask (hackathon lean)."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.time()
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max_calls:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")
        q.append(now)


upload_limiter = RateLimiter(max_calls=30, window_seconds=60)
ask_limiter = RateLimiter(max_calls=20, window_seconds=60)


def client_key(request: Request, user_id: int | None = None) -> str:
    host = request.client.host if request.client else "unknown"
    if user_id is not None:
        return f"u:{user_id}"
    return f"ip:{host}"
