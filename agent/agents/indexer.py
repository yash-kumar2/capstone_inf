from __future__ import annotations

import argparse
import os
import uuid
from typing import Any

from agent.db import get_conn
from agent.llm import embed
from agent.settings import SETTINGS

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except Exception:  # pragma: no cover
    QdrantClient = None
    qmodels = None


COLLECTION_NAME = "invoices_rag"


def _client() -> Any | None:
    if QdrantClient is None:
        return None
    try:
        return QdrantClient(host=SETTINGS.get("QDRANT_HOST", "localhost"), port=int(SETTINGS.get("QDRANT_PORT", "6333")))
    except Exception:
        return None


def ensure_collection() -> None:
    client = _client()
    if client is None:
        return
    try:
        existing = client.get_collection(collection_name=COLLECTION_NAME)
        if existing:
            return
    except Exception:
        pass

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=qmodels.VectorParams(size=int(SETTINGS.get("EMBED_DIM", 1024)), distance=qmodels.Distance.COSINE),
    )


def _report_to_text(report: dict[str, Any] | None) -> str:
    if not report:
        return ""
    invoice = report.get("invoice_summary", {})
    return (
        f"Invoice {invoice.get('invoice_number', 'n/a')} for {invoice.get('vendor_name', 'n/a')} "
        f"has validation status {report.get('validation_status', 'unknown')} and recommendation {report.get('recommendation', 'review')}."
    )


def index_invoice(invoice_id: str) -> None:
    client = _client()
    if client is None:
        return
    ensure_collection()

    sql = """
        SELECT invoice_id, file_name, file_type, source_language, raw_extracted_text, translated_text,
               invoice_number, vendor_name, report_json
        FROM audit.invoice_audit
        WHERE invoice_id = %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (invoice_id,))
            row = cur.fetchone()
            if row is None:
                return

    payloads: list[dict[str, Any]] = []
    row_dict = dict(zip(["invoice_id", "file_name", "file_type", "source_language", "raw_extracted_text", "translated_text", "invoice_number", "vendor_name", "report_json"], row))
    invoice_number = row_dict.get("invoice_number") or "unknown"
    source_language = row_dict.get("source_language") or "en"
    raw_text = row_dict.get("raw_extracted_text") or ""
    translated_text = row_dict.get("translated_text") or raw_text

    def add_payload(text: str, source_type: str, language: str, chunk_index: int) -> None:
        if not text:
            return
        payloads.append({
            "invoice_id": str(invoice_id),
            "invoice_number": invoice_number,
            "source_type": source_type,
            "vendor": row_dict.get("vendor_name"),
            "language": language,
            "chunk_index": chunk_index,
            "chunk_text": text,
        })

    if raw_text:
        for idx, chunk in enumerate([raw_text]):
            add_payload(chunk, "invoice", source_language, idx)
    if translated_text and translated_text != raw_text:
        for idx, chunk in enumerate([translated_text]):
            add_payload(chunk, "invoice", "en", idx)
    report_text = _report_to_text(row_dict.get("report_json"))
    if report_text:
        add_payload(report_text, "report", "en", 0)

    if not payloads:
        return

    vectors = embed([payload["chunk_text"] for payload in payloads])
    points = []
    for idx, (payload, vector) in enumerate(zip(payloads, vectors)):
        point_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{payload['invoice_id']}:{payload['source_type']}:{payload['language']}:{payload['chunk_index']}")
        points.append({
            "id": str(point_id),
            "vector": vector,
            "payload": payload,
        })

    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)


def reindex_all() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT invoice_id FROM audit.invoice_audit WHERE processing_status = 'completed' ORDER BY detected_at")
            rows = cur.fetchall()
    for (invoice_id,) in rows:
        index_invoice(str(invoice_id))


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the invoice Qdrant index")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    if args.rebuild:
        reindex_all()


if __name__ == "__main__":
    main()
