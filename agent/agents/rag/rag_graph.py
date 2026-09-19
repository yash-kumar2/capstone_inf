from __future__ import annotations

from typing import Any

from .reflection import evaluate_answer, should_pass


def run_rag_round(question: str, attempt_callback: Any | None = None, max_attempts: int = 3) -> dict[str, Any]:
    best_result = None
    best_score = -1.0
    attempts = 0

    for attempt in range(1, max_attempts + 1):
        attempts = attempt
        if attempt_callback is None:
            result = {
                "answer": f"Best effort answer for: {question}",
                "mode": "rag",
                "sources": [],
                "scores": {"relevance": 0.2, "groundedness": 0.2, "context_relevance": 0.2},
            }
        else:
            result = attempt_callback(question, attempt)

        scores = evaluate_answer(result.get("scores", {}))
        avg_score = scores.get("average", 0.0)
        if avg_score > best_score:
            best_score = avg_score
            best_result = result

        if should_pass(result.get("scores", {})):
            final = dict(result)
            final["attempts"] = attempts
            final["low_confidence"] = False
            final["scores"] = evaluate_answer(result.get("scores", {}))
            return final

    if not best_result:
        best_result = {
            "answer": f"No reliable answer found for: {question}",
            "mode": "rag",
            "sources": [],
            "scores": {"relevance": 0.0, "groundedness": 0.0, "context_relevance": 0.0},
        }

    best_result["attempts"] = attempts
    best_result["low_confidence"] = True
    best_result["scores"] = evaluate_answer(best_result.get("scores", {}))
    return best_result
