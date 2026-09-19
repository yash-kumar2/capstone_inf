from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from .agents.rag.rag_graph import run_rag_round
from .agents.rag.router import route_question
from .agents.rag.sql_answers import answer_sql_question
from .settings import SETTINGS

app = FastAPI(title="AI Invoice Auditor Agent")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "postgres": SETTINGS["POSTGRES_DB"],
        "redis": SETTINGS["REDIS_HOST"],
        "qdrant": SETTINGS["QDRANT_HOST"],
    }


@app.post("/query")
def query(payload: dict[str, Any]) -> dict[str, Any]:
    question = str(payload.get("question", "")).strip()
    if not question:
        return {"answer": "No question provided.", "mode": "sql", "sources": [], "scores": {"relevance": 0.0, "groundedness": 0.0, "context_relevance": 0.0}, "attempts": 0, "low_confidence": True}

    mode = route_question(question)
    if mode == "sql":
        return answer_sql_question(question)

    result = run_rag_round(question)
    result.setdefault("mode", "rag")
    return result
