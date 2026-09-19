from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from .agents.rag.rag_graph import run_rag_round
from .agents.rag.router import route_question
from .agents.rag.sql_answers import answer_sql_question
from .db import get_effective_invoice, save_feedback
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


@app.post("/feedback")
def feedback(payload: dict[str, Any]) -> dict[str, Any]:
    invoice_id = payload.get("invoice_id")
    field_name = str(payload.get("field_name", ""))
    corrected_by = str(payload.get("corrected_by", "unknown"))
    if not invoice_id or not field_name:
        raise HTTPException(status_code=422, detail="invoice_id and field_name are required")

    if not field_name.startswith("line_items[") and field_name not in {"invoice_number", "invoice_date", "vendor_name", "po_number", "currency", "subtotal", "tax_amount", "total_amount"}:
        raise HTTPException(status_code=422, detail=f"Unsupported field_name: {field_name}")

    save_feedback(
        str(invoice_id),
        field_name,
        payload.get("original_value"),
        payload.get("corrected_value"),
        corrected_by,
    )
    return {"status": "ok", "field_name": field_name}


@app.get("/invoices/{invoice_id}/effective")
def effective_invoice(invoice_id: str) -> dict[str, Any]:
    invoice = {"invoice_id": invoice_id}
    return get_effective_invoice(invoice, [])
