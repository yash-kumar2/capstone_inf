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


def save_translation(invoice_id: str, source_language: str, translated_text: str, translation_confidence: float) -> None:
    sql = """
        UPDATE audit.invoice_audit
        SET source_language = %s, translated_text = %s, translation_confidence = %s
        WHERE invoice_id = %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (source_language, translated_text, translation_confidence, invoice_id))


def save_parsed(invoice_id: str, invoice: dict, line_items: list[dict]) -> None:
    sql = """
        UPDATE audit.invoice_audit
        SET invoice_number = %s,
            invoice_date = %s,
            vendor_name = %s,
            po_number = %s,
            currency = %s,
            subtotal = %s,
            tax_amount = %s,
            total_amount = %s,
            processing_status = 'parsed'
        WHERE invoice_id = %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    invoice.get("invoice_number"),
                    invoice.get("invoice_date"),
                    invoice.get("vendor_name"),
                    invoice.get("po_number"),
                    invoice.get("currency"),
                    invoice.get("subtotal"),
                    invoice.get("tax_amount"),
                    invoice.get("total_amount"),
                    invoice_id,
                ),
            )
            cur.execute("DELETE FROM audit.invoice_line_items WHERE invoice_id = %s", (invoice_id,))
            for line in line_items:
                cur.execute(
                    """
                        INSERT INTO audit.invoice_line_items (invoice_id, line_number, item_code, description, quantity, unit_price, line_total)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        invoice_id,
                        line.get("line_number"),
                        line.get("item_code"),
                        line.get("description"),
                        line.get("quantity"),
                        line.get("unit_price"),
                        line.get("line_total"),
                    ),
                )
