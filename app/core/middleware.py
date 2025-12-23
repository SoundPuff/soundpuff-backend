import time
from collections import deque
from typing import Callable, Deque, Dict, Tuple
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding configured body size."""

    def __init__(self, app, max_body_size: int):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next: Callable):
        raw_content_length = request.headers.get("content-length")
        if raw_content_length:
            try:
                content_length = int(raw_content_length)
                if content_length > self.max_body_size:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large"},
                    )
            except ValueError:
                # Fall through to validated body check below if Content-Length is malformed.
                pass

        # Read once with an upper bound and re-inject so downstream handlers can still consume it.
        body = await request.body()
        if len(body) > self.max_body_size:
            return JSONResponse(status_code=413, content={"detail": "Request body too large"})

        async def receive() -> dict:
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive  # type: ignore[attr-defined]
        return await call_next(request)


class SimpleRateLimiterMiddleware(BaseHTTPMiddleware):
    """Naive in-process sliding window rate limiter (per client IP per prefix)."""

    def __init__(self, app, rules: Dict[str, Dict[str, int]]):
        super().__init__(app)
        # rules: prefix -> {"limit": int, "window_seconds": int}
        self.rules = rules
        self._buckets: Dict[Tuple[str, str], Deque[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        matched_rule = None
        for prefix, rule in self.rules.items():
            if path.startswith(prefix):
                matched_rule = (prefix, rule)
                break

        if matched_rule:
            prefix, rule = matched_rule
            limit = rule.get("limit", 0)
            window = rule.get("window_seconds", 60)
            bucket_key = (client_ip, prefix)
            bucket = self._buckets.setdefault(bucket_key, deque())
            now = time.time()

            while bucket and bucket[0] <= now - window:
                bucket.popleft()

            if limit and len(bucket) >= limit:
                retry_after = max(1, int(window - (now - bucket[0]))) if bucket else window
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                    content={"detail": "Rate limit exceeded"},
                )

            bucket.append(now)

        response = await call_next(request)
        return response
