from __future__ import annotations

from typing import Any

import psycopg

from .settings import SETTINGS


def get_conn() -> psycopg.Connection:
    return psycopg.connect(
        dbname=SETTINGS["POSTGRES_DB"],
        user=SETTINGS["POSTGRES_USER"],
        password=SETTINGS["POSTGRES_PASSWORD"],
        host=SETTINGS["POSTGRES_HOST"],
        port=SETTINGS["POSTGRES_PORT"],
    )


def claim_invoice(file_path: str, name: str, file_type: str, checksum: str) -> str | None:
    sql = """
        INSERT INTO audit.invoice_audit (file_path, file_name, file_type, file_checksum, processing_status)
        VALUES (%s, %s, %s, %s, 'detected')
        ON CONFLICT (file_checksum) DO NOTHING
        RETURNING invoice_id
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (file_path, name, file_type, checksum))
            row = cur.fetchone()
            if row is None:
                return None
            return str(row[0])
