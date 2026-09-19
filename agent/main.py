from __future__ import annotations

import logging
import os
import shutil
from typing import Any

import httpx
import psycopg
import redis
from fastapi import FastAPI, HTTPException
from qdrant_client import QdrantClient

from .agents.rag.rag_graph import run_rag_round
from .agents.rag.router import route_question
from .agents.rag.sql_answers import answer_sql_question
from .db import get_effective_invoice, save_feedback
from .settings import SETTINGS

logging.basicConfig(level=getattr(logging, SETTINGS["LOG_LEVEL"].upper(), logging.INFO), format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("invoice-agent")

app = FastAPI(title="AI Invoice Auditor Agent")


def validate_runtime_dependencies() -> None:
    missing = []
    for key in ["MODEL_REASONING", "MODEL_GENERATION", "MODEL_TRANSLATION", "MODEL_EMBEDDING"]:
        if not SETTINGS.get(key):
            missing.append(key)
    if not shutil.which("tesseract"):
        missing.append("tesseract")
    if missing:
        raise RuntimeError(f"Startup validation failed: missing runtime requirements: {', '.join(missing)}")

    try:
        with psycopg.connect(
            dbname=SETTINGS["POSTGRES_DB"],
            user=SETTINGS["POSTGRES_USER"],
            password=SETTINGS["POSTGRES_PASSWORD"],
            host=SETTINGS["POSTGRES_HOST"],
            port=SETTINGS["POSTGRES_PORT"],
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:  # pragma: no cover - startup guard
        raise RuntimeError(f"PostgreSQL startup check failed: {exc}") from exc

    try:
        redis_client = redis.Redis(host=SETTINGS["REDIS_HOST"], port=SETTINGS["REDIS_PORT"], decode_responses=True)
        redis_client.ping()
    except Exception as exc:  # pragma: no cover - startup guard
        raise RuntimeError(f"Redis startup check failed: {exc}") from exc

    try:
        qdrant_client = QdrantClient(host=SETTINGS["QDRANT_HOST"], port=SETTINGS["QDRANT_PORT"])
        qdrant_client.get_collections()
    except Exception as exc:  # pragma: no cover - startup guard
        raise RuntimeError(f"Qdrant startup check failed: {exc}") from exc

    try:
        response = httpx.get(f"{SETTINGS['ERP_BASE_URL']}/health", timeout=5.0)
        if response.status_code != 200:
            raise RuntimeError(f"ERP health check returned {response.status_code}")
    except Exception as exc:  # pragma: no cover - startup guard
        raise RuntimeError(f"ERP startup check failed: {exc}") from exc


@app.on_event("startup")
def startup_checks() -> None:
    logger.info("Running startup dependency validation")
    validate_runtime_dependencies()
    logger.info("Startup dependency validation passed")


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
