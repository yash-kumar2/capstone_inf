from __future__ import annotations

import re
from typing import Any


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def rerank_chunks(question: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_question = _normalize_text(question)
    invoice_ref = None
    match = re.search(r"invoice\s*([A-Z0-9-]+)", normalized_question, flags=re.IGNORECASE)
    if match:
        invoice_ref = match.group(1)

    scored: list[dict[str, Any]] = []
    for chunk in chunks:
        score = float(chunk.get("score", 0.0))
        payload = dict(chunk)
        if "reject" in normalized_question or "discrepancy" in normalized_question or "why" in normalized_question:
            if payload.get("source_type") == "report":
                score += 0.12
        if invoice_ref:
            invoice_number = str(payload.get("invoice_number", "")).lower()
            if invoice_ref in invoice_number:
                score += 0.10
        payload["final_score"] = score
        scored.append(payload)

    return sorted(scored, key=lambda item: item["final_score"], reverse=True)


def augment(question: str, chunks: list[dict[str, Any]], max_chars: int = 2000) -> list[str]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chunk in rerank_chunks(question, chunks):
        text = str(chunk.get("text", "")).strip()
        key = _normalize_text(text)
        if not text or key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for chunk in deduped:
        grouped.setdefault(str(chunk.get("invoice_id", "unknown")), []).append(chunk)

    blocks: list[str] = []
    for invoice_id, items in grouped.items():
        selected = []
        used = 0
        for item in items:
            label = str(item.get("source_type", "invoice")).upper()
            invoice_number = str(item.get("invoice_number", invoice_id))
            segment = f"[{label} | {invoice_number}] {item.get('text', '')}"
            if used + len(segment) > max_chars:
                break
            selected.append(segment)
            used += len(segment)
        if selected:
            blocks.append("\n".join(selected))

    if not blocks:
        for chunk in deduped[:3]:
            blocks.append(str(chunk.get("text", "")).strip())

    return blocks
