from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from .cache import cache_get, cache_set

try:
    import litellm
except Exception:  # pragma: no cover
    litellm = None


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _strip_json_fences(text: str) -> str:
    if text is None:
        return ""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def chat(model_key: str, messages: list[dict[str, str]], temperature: float = 0, json: bool = False, cache: bool = True) -> str:
    if litellm is None:
        raise RuntimeError("litellm is not installed")

    cache_key = f"llm:{_hash(json.dumps({'model_key': model_key, 'messages': messages, 'temperature': temperature}, sort_keys=True))}"
    if cache:
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

    kwargs = {
        "model": model_key,
        "messages": messages,
        "temperature": temperature,
        "num_retries": 3,
    }
    if json:
        kwargs["response_format"] = {"type": "json_object"}

    response = litellm.completion(**kwargs)
    content = response.choices[0].message.content or ""
    normalized = _strip_json_fences(content) if json else content
    if cache:
        cache_set(cache_key, normalized)
    return normalized


def embed(texts: list[str]) -> list[list[float]]:
    if litellm is None:
        raise RuntimeError("litellm is not installed")

    results: list[list[float]] = []
    for text in texts:
        cache_key = f"llm:embed:{_hash(text)}"
        cached = cache_get(cache_key)
        if cached is not None:
            results.append(cached)
            continue

        response = litellm.embedding(model=os.getenv("MODEL_EMBEDDING", "bedrock/amazon.titan-embed-text-v2:0"), input=[text])
        data = getattr(response, "data", None) or []
        vector = data[0]["embedding"] if data and isinstance(data[0], dict) and "embedding" in data[0] else []
        if not vector and hasattr(data[0], "embedding"):
            vector = data[0].embedding
        cache_set(cache_key, vector)
        results.append(vector)
    return results
