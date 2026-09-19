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


def log_file_event(invoice_id: str | None, file_path: str, file_checksum: str, event: str, detail: str | None = None) -> None:
    sql = """
        INSERT INTO audit.file_events (invoice_id, file_path, file_checksum, event, detail)
        VALUES (%s, %s, %s, %s, %s)
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (invoice_id, file_path, file_checksum, event, detail))


def set_status(invoice_id: str | None, processing_status: str) -> None:
    if invoice_id is None:
        return
    sql = "UPDATE audit.invoice_audit SET processing_status = %s, processed_at = NOW() WHERE invoice_id = %s"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (processing_status, invoice_id))


def mark_error(invoice_id: str | None, error_message: str, detail: str | None = None) -> None:
    if invoice_id is None:
        return
    sql = "UPDATE audit.invoice_audit SET processing_status = 'error', error_message = %s WHERE invoice_id = %s"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (error_message, invoice_id))
    if detail:
        log_file_event(invoice_id, detail, "", "error", error_message)
