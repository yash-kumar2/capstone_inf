from __future__ import annotations

import json
import os
from typing import Any

from .agents.invoice_validator import validate_invoice
from .agents.business_validator import business_validate
from .agents.reporter import build_report, render_html_report
from .db import save_report, save_validation
from .settings import SETTINGS
from .tools.erp_tools import ErpClient

try:
    from psycopg_pool import ConnectionPool
    from psycopg.rows import dict_row
    from langgraph.checkpoint.postgres import PostgresSaver
except Exception:  # pragma: no cover
    ConnectionPool = None
    dict_row = None
    PostgresSaver = None


def _load_rules() -> dict[str, Any]:
    file_path = os.path.join(os.path.dirname(__file__), "configs", "rules.yaml")
    if not os.path.exists(file_path):
        return {}
    try:
        import yaml

        with open(file_path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except Exception:
        return {}


def monitor(state: dict[str, Any]) -> dict[str, Any]:
    return state


def extract(state: dict[str, Any]) -> dict[str, Any]:
    return state


def translate(state: dict[str, Any]) -> dict[str, Any]:
    return state


def parse(state: dict[str, Any]) -> dict[str, Any]:
    return state


def validate_internal(state: dict[str, Any]) -> dict[str, Any]:
    invoice = state.get("invoice", {})
    line_items = state.get("line_items", [])
    result = validate_invoice(invoice, line_items, _load_rules())
    state["internal_validation"] = result
    state["validation_status"] = result.get("validation_status", "passed")
    return state


def validate_erp(state: dict[str, Any]) -> dict[str, Any]:
    invoice = state.get("invoice", {})
    line_items = state.get("line_items", [])
    client = ErpClient(SETTINGS.get("ERP_BASE_URL", "http://localhost:8001"))
    result = business_validate(invoice, line_items, _load_rules(), client)
    state["erp_validation"] = result
    state["validation_status"] = result.get("validation_status", state.get("validation_status", "passed"))
    return state


def report(state: dict[str, Any]) -> dict[str, Any]:
    invoice = state.get("invoice", {})
    internal_validation = state.get("internal_validation", {})
    erp_validation = state.get("erp_validation", {})
    rules = _load_rules()

    report_payload = build_report(
        invoice=invoice,
        internal_validation=internal_validation,
        erp_validation=erp_validation,
        source_language=state.get("source_language"),
        translation_confidence=state.get("translation_confidence"),
        rules=rules,
    )
    html_payload = render_html_report(report_payload)
    state["report"] = report_payload
    state["recommendation"] = report_payload["recommendation"]
    state["validation_status"] = report_payload["validation_status"]

    invoice_id = state.get("invoice_id")
    if invoice_id:
        save_validation(invoice_id, 1, "combined", report_payload["discrepancy_summary"]["items"])
        save_report(invoice_id, report_payload, html_payload, report_payload["recommendation"], report_payload["validation_status"])
    return state


def index_document(state: dict[str, Any]) -> dict[str, Any]:
    return state


def handle_error(state: dict[str, Any], error: Exception | str | None = None) -> dict[str, Any]:
    state["error"] = str(error) if error is not None else "Unknown pipeline error"
    state["validation_status"] = "failed"
    return state


def setup_postgres_saver() -> Any:
    if PostgresSaver is None or ConnectionPool is None:
        return None

    pool = ConnectionPool(
        conninfo=(
            f"dbname={os.getenv('POSTGRES_DB', 'invoice_auditor')} "
            f"user={os.getenv('POSTGRES_USER', 'postgres')} "
            f"password={os.getenv('POSTGRES_PASSWORD', 'postgres')} "
            f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
            f"port={os.getenv('POSTGRES_PORT', '5432')}"
        ),
        min_size=1,
        max_size=5,
        kwargs={"autocommit": True, "row_factory": dict_row, "options": "-c search_path=langgraph"},
    )
    saver = PostgresSaver(pool)
    saver.setup()
    return saver


def build_graph() -> dict[str, Any]:
    return {
        "nodes": [
            "monitor",
            "extract",
            "translate",
            "parse",
            "validate_internal",
            "validate_erp",
            "report",
            "index_document",
        ],
        "edges": [
            ("monitor", "extract"),
            ("extract", "translate"),
            ("translate", "parse"),
            ("parse", "validate_internal"),
            ("validate_internal", "validate_erp"),
            ("validate_erp", "report"),
            ("report", "index_document"),
        ],
    }
