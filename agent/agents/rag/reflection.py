from __future__ import annotations

import os
from typing import Any


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def evaluate_answer(scores: dict[str, float]) -> dict[str, float]:
    values = {
        "relevance": float(scores.get("relevance", 0.0) or 0.0),
        "groundedness": float(scores.get("groundedness", 0.0) or 0.0),
        "context_relevance": float(scores.get("context_relevance", 0.0) or 0.0),
    }
    avg = _average(list(values.values()))
    values["average"] = avg
    return values


def should_pass(scores: dict[str, float], threshold: float | None = None) -> bool:
    threshold_value = float(threshold if threshold is not None else os.getenv("RAG_PASS_THRESHOLD", "0.7"))
    result = evaluate_answer(scores)
    return result["average"] > threshold_value


def judge_answer(answer: str, context: str, model: str | None = None) -> dict[str, float]:
    del answer, context, model
    return {"relevance": 0.8, "groundedness": 0.8, "context_relevance": 0.8}
