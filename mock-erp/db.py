from __future__ import annotations

import time
from typing import Any

import psycopg


def _get_connection_kwargs() -> dict[str, Any]:
    import os

    return {
        "dbname": os.getenv("POSTGRES_DB", "invoice_auditor"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
    }


def get_conn() -> psycopg.Connection:
    for attempt in range(1, 7):
        try:
            return psycopg.connect(**_get_connection_kwargs())
        except Exception:
            if attempt == 6:
                raise
            time.sleep(1)
    raise RuntimeError("Unable to connect to PostgreSQL")
