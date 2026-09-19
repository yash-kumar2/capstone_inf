# Demo guide

## End-to-end flow

1. Place an invoice in the incoming directory.
2. The monitor detects the file, computes a checksum, and stores a file event.
3. The agent extracts OCR or document text, translates if needed, and parses the invoice.
4. Validation compares the parsed fields to internal arithmetic and ERP-backed controls.
5. The report is saved and shown in the Streamlit dashboard.
6. The auditor asks a question in the agent API or UI; the system answers using SQL or retrieval augmented generation.

## Suggested live demo script

- Open the Streamlit UI at http://localhost:8501.
- Confirm the database is connected and no invoices are yet visible.
- Drop a sample file into incoming/.
- Wait for the monitor to process it and show the new invoice in the table.
- Open the report and explain the mismatch summary.
- Use an example question like: "What invoice is over budget?" or "Which vendor has the missing PO?"
- Show the RAG answer and explain whether the system used SQL routing or vector retrieval.

## Key commands

```bash
docker compose up --build -d
python -m pytest agent/tests -q
./scripts/verify_all.sh
```
