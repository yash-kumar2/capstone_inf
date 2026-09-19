# Viva notes

## What problem this solves

The project automates invoice intake, validation, and audit reasoning. It reduces manual invoice review by combining OCR, language handling, deterministic validation, and retrieval-backed analysis.

## Why this architecture works

- PostgreSQL persists the invoice audit trail and report data.
- Redis caches translation and model calls.
- Qdrant stores semantic invoice/report chunks for retrieval.
- The mock ERP supplies authoritative vendor and PO context.
- The Streamlit front end keeps the process visible to non-technical auditors.

## Key design decisions

- Arithmetic and validation rules are deterministic to avoid brittle LLM logic.
- Human feedback is stored immutably and applied as an overlay when effective values are calculated.
- The agent routes simple questions to SQL and more open-ended questions to RAG.
- Docker health checks and fail-fast startup reduce half-started services.

## Evidence

- Project tests pass with `pytest agent/tests -q`.
- The environment is hardened with health checks, dependency validation, and secret scanning helpers.
- The verification scripts confirm schema, persistence, and operational checks.
