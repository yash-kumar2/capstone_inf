from __future__ import annotations

import json
import os
import re
from decimal import Decimal, InvalidOperation
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


def save_feedback(invoice_id: str, field_name: str, original_value: Any, corrected_value: Any, corrected_by: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                    INSERT INTO audit.human_feedback (invoice_id, field_name, original_value, corrected_value, corrected_by)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                (invoice_id, field_name, str(original_value) if original_value is not None else None, str(corrected_value) if corrected_value is not None else None, corrected_by),
            )


def _coerce_feedback_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, Decimal)):
        return value

    text = str(value).strip()
    if text == "":
        return value

    try:
        decimal_value = Decimal(text)
    except InvalidOperation:
        return value

    if decimal_value == decimal_value.to_integral_value():
        return int(decimal_value)
    return float(decimal_value)


def get_effective_invoice(invoice: dict[str, Any] | str | None, line_items: list[dict[str, Any]] | None = None, feedback: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if isinstance(invoice, str):
        invoice = {"invoice_id": invoice}

    invoice_data = dict(invoice or {})
    line_items_data = list(line_items or [])
    feedback_rows = list(feedback or [])

    if not feedback_rows and invoice_data.get("invoice_id"):
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT field_name, original_value, corrected_value, corrected_by, corrected_at
                    FROM audit.human_feedback
                    WHERE invoice_id = %s
                    ORDER BY corrected_at DESC, id DESC
                    """,
                    (invoice_data["invoice_id"],),
                )
                feedback_rows = [
                    {
                        "field_name": row[0],
                        "original_value": row[1],
                        "corrected_value": row[2],
                        "corrected_by": row[3],
                        "corrected_at": row[4],
                    }
                    for row in cur.fetchall()
                ]

    corrections_by_field: dict[str, Any] = {}
    for row in feedback_rows:
        field_name = row.get("field_name")
        if field_name:
            corrections_by_field[field_name] = _coerce_feedback_value(row.get("corrected_value"))

    for field_name, corrected_value in corrections_by_field.items():
        if field_name.startswith("line_items["):
            continue
        invoice_data[field_name] = corrected_value

    updated_line_items: list[dict[str, Any]] = []
    for item in line_items_data:
        entry = dict(item)
        for row in feedback_rows:
            field_name = row.get("field_name")
            match = re.match(r"line_items\[(\d+)\]\.(.+)", str(field_name or ""))
            if not match:
                continue
            line_number = int(match.group(1))
            property_name = match.group(2)
            if int(entry.get("line_number", 0)) == line_number:
                entry[property_name] = _coerce_feedback_value(row.get("corrected_value"))
        updated_line_items.append(entry)

    invoice_data["line_items"] = updated_line_items
    return invoice_data


def save_validation(invoice_id: str, run: int, source: str, discrepancies: list[dict]) -> None:
    if invoice_id is None:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE audit.invoice_audit SET validation_run = %s, validation_status = %s WHERE invoice_id = %s",
                (run, "failed" if discrepancies else "passed", invoice_id),
            )
            for item in discrepancies:
                cur.execute(
                    """
                        INSERT INTO audit.discrepancies (
                            invoice_id, source, line_number, field_name, invoice_value, expected_value,
                            deviation_pct, severity, message, validation_run
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        invoice_id,
                        item.get("source", source),
                        item.get("line_number"),
                        item.get("field_name"),
                        item.get("invoice_value"),
                        item.get("expected_value"),
                        item.get("deviation_pct"),
                        item.get("severity"),
                        item.get("message"),
                        run,
                    ),
                )


def write_report_files(invoice_id: str, report_json: dict, report_html: str, report_dir: str = "/data/reports") -> None:
    os.makedirs(report_dir, exist_ok=True)
    base_path = os.path.join(report_dir, str(invoice_id))
    json_path = f"{base_path}.json"
    html_path = f"{base_path}.html"

    temp_json_path = f"{json_path}.tmp"
    temp_html_path = f"{html_path}.tmp"

    with open(temp_json_path, "w", encoding="utf-8") as handle:
        json.dump(report_json, handle, ensure_ascii=False, indent=2, default=str)
    os.replace(temp_json_path, json_path)

    with open(temp_html_path, "w", encoding="utf-8") as handle:
        handle.write(report_html)
    os.replace(temp_html_path, html_path)


def save_report(invoice_id: str, report_json: dict, report_html: str, recommendation: str, validation_status: str) -> None:
    if invoice_id is None:
        return
    write_report_files(invoice_id, report_json, report_html)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                    UPDATE audit.invoice_audit
                    SET report_json = %s,
                        report_html = %s,
                        recommendation = %s,
                        validation_status = %s,
                        processing_status = 'completed',
                        processed_at = NOW()
                    WHERE invoice_id = %s
                """,
                (report_json, report_html, recommendation, validation_status, invoice_id),
            )
