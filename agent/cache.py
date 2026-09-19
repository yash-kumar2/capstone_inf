from __future__ import annotations

import json
import os
from typing import Any

try:
    import redis
except Exception:  # pragma: no cover
    redis = None


class CacheClient:
    def __init__(self) -> None:
        self._ttl = int(os.getenv("CACHE_TTL_SECONDS", "604800"))
        self._client = None
        if redis is not None:
            try:
                self._client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", "6379")),
                    decode_responses=True,
                )
                self._client.ping()
            except Exception:
                self._client = None

    def get(self, key: str) -> Any:
        if self._client is None:
            return None
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            try:
                return json.loads(raw)
            except Exception:
                return raw
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if self._client is None:
            return
        try:
            payload = json.dumps(value) if not isinstance(value, str) else value
            self._client.set(key, payload, ex=ttl or self._ttl)
        except Exception:
            pass


CACHE = CacheClient()


def cache_get(key: str) -> Any:
    return CACHE.get(key)


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    CACHE.set(key, value, ttl)
