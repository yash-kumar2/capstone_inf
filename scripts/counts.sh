#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

printf 'audit.invoice_audit: '
docker compose exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-invoice_auditor}" -At -c "SELECT count(*) FROM audit.invoice_audit;"
printf 'audit.invoice_line_items: '
docker compose exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-invoice_auditor}" -At -c "SELECT count(*) FROM audit.invoice_line_items;"
printf 'audit.discrepancies: '
docker compose exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-invoice_auditor}" -At -c "SELECT count(*) FROM audit.discrepancies;"
printf 'audit.file_events: '
docker compose exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-invoice_auditor}" -At -c "SELECT count(*) FROM audit.file_events;"
printf 'qdrant.invoices_rag: '
docker compose exec -T agent python -c "import os; from qdrant_client import QdrantClient; client = QdrantClient(host=os.getenv('QDRANT_HOST', 'qdrant'), port=int(os.getenv('QDRANT_PORT', '6333'))); print(client.get_collection('invoices_rag').points_count)"
