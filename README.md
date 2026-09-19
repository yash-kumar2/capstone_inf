# AI Invoice Auditor

AI Invoice Auditor is a full-stack invoice processing and review system that monitors inbound invoice files, parses and validates them, cross-checks against ERP data, and answers audit questions through SQL or retrieval-augmented generation.

## What is included

- File intake and duplicate detection
- OCR and document extraction for PDF, DOCX, and PNG flows
- Language detection and translation
- Deterministic parsing and validation logic
- ERP validation against vendor, PO, and SKU data
- Human feedback overlay for corrected invoice values
- PostgreSQL persistence with auditing and report storage
- Qdrant-backed retrieval for document and invoice search
- Streamlit dashboard for invoice review
- Dockerized infrastructure and runtime hardening

## Quick start

1. Copy `.env.example` to `.env` and fill in the required values.
2. Start the infrastructure stack:
   `docker compose up --build -d`
3. Open the UI at http://localhost:8501.
4. Optionally run the regression tests:
   `python -m pytest agent/tests -q`
5. Run the verification bundle:
   `bash scripts/verify_all.sh`

## Required structure

- `agent/` - FastAPI service, validators, RAG, and settings
- `mock-erp/` - ERP API used for vendor and PO checks
- `streamlit-ui/` - invoice dashboard
- `db/` - PostgreSQL schema and audit tables
- `scripts/` - runtime validation and persistence checks
- `docs/` - architecture, demo, and viva notes
- `samples/` - demo invoice set for validation and dry runs

## Verified status

The project is validated through the Python regression suite and the operational scripts included in the repo. The latest milestone is the final documentation and hardening pass.

## Commit history summary

- Commit 1: scaffold and infrastructure
- Commit 2: intake, ERP service, LLM wrapper
- Commit 3: extraction and validation
- Commit 4: translation and parsing
- Commit 5: validation reporting and persistence
- Commit 6: Qdrant indexing and retrieval
- Commit 7: SQL/RAG routing and reflection loop
- Commit 8: human feedback overlay and effective invoice corrections
- Commit 9: Docker hardening and startup checks
- Commit 10: final verification, documentation, and release packaging
