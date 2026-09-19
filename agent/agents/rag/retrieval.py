from __future__ import annotations

import os
import re
from typing import Any

from agent.db import get_conn
from agent.llm import embed as llm_embed

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except Exception:  # pragma: no cover
    QdrantClient = None
    qmodels = None


def _client() -> Any | None:
    if QdrantClient is None:
        return None
    try:
        return QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"), port=int(os.getenv("QDRANT_PORT", "6333")))
    except Exception:
        return None


def _build_filter(invoice_id: str | None = None, vendor: str | None = None, source_types: list[str] | None = None) -> Any | None:
    if qmodels is None:
        return None
    conditions: list[Any] = []
    if invoice_id:
        conditions.append(qmodels.FieldCondition(key="invoice_id", match=qmodels.MatchValue(value=invoice_id)))
    if vendor:
        conditions.append(qmodels.FieldCondition(key="vendor", match=qmodels.MatchValue(value=vendor)))
    if source_types:
        values = [str(item) for item in source_types]
        if values:
            conditions.append(qmodels.FieldCondition(key="source_type", match=qmodels.MatchAny(any=values)))
    if not conditions:
        return None
    return qmodels.Filter(must=conditions)


def retrieve(question: str, invoice_id: str | None = None, vendor: str | None = None, source_types: list[str] | None = None, k: int = 8) -> list[dict[str, Any]]:
    client = _client()
    if client is None:
        return []
    try:
        vector = llm_embed([question])[0]
        filter_ = _build_filter(invoice_id=invoice_id, vendor=vendor, source_types=source_types)
        results = client.search(
            collection_name="invoices_rag",
            query_vector=vector,
            query_filter=filter_,
            limit=max(1, int(k)),
            with_payload=True,
        )
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    for item in results:
        payload = getattr(item, "payload", {}) or {}
        rows.append(
            {
                "text": payload.get("chunk_text"),
                "invoice_id": payload.get("invoice_id"),
                "source_type": payload.get("source_type"),
                "invoice_number": payload.get("invoice_number"),
                "vendor": payload.get("vendor"),
                "score": float(getattr(item, "score", 0.0) or 0.0),
                "language": payload.get("language"),
            }
        )
    return rows


def resolve_invoice_ref(question: str) -> str | None:
    match = re.search(r"invoice\s*([A-Z0-9-]+)", question, flags=re.IGNORECASE)
    if match:
        ref = match.group(1)
    else:
        return None

    sql = "SELECT invoice_id FROM audit.invoice_audit WHERE invoice_number = %s LIMIT 1"
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (ref,))
                row = cur.fetchone()
                if row:
                    return str(row[0])
    except Exception:
        pass
    return None
