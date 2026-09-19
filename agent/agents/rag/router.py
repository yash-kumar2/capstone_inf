from __future__ import annotations

import re


STRUCTURED_PATTERNS = (
    "total amount",
    "invoice total",
    "count by status",
    "status of invoice",
    "invoices by vendor",
    "month",
    "discrepancies",
    "rejected",
)


def route_question(question: str) -> str:
    text = (question or "").lower()
    invoice_match = re.search(r"invoice\s*([a-z0-9-]+)", text, flags=re.IGNORECASE)

    if any(keyword in text for keyword in ("why", "reject", "rejected", "flag", "discrepancy", "failed")):
        return "rag"

    is_structured = any(pattern in text for pattern in STRUCTURED_PATTERNS)
    if is_structured and invoice_match:
        return "sql"

    if "total" in text or "status" in text or "count" in text or "vendor" in text:
        return "sql"

    return "rag"
