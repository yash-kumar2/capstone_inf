from __future__ import annotations

import os
from typing import Any

try:
    from psycopg_pool import ConnectionPool
    from psycopg.rows import dict_row
    from langgraph.checkpoint.postgres import PostgresSaver
except Exception:  # pragma: no cover
    ConnectionPool = None
    dict_row = None
    PostgresSaver = None


def monitor(state: dict[str, Any]) -> dict[str, Any]:
    return state


def extract(state: dict[str, Any]) -> dict[str, Any]:
    return state


def translate(state: dict[str, Any]) -> dict[str, Any]:
    return state


def parse(state: dict[str, Any]) -> dict[str, Any]:
    return state


def validate_internal(state: dict[str, Any]) -> dict[str, Any]:
    return state


def validate_erp(state: dict[str, Any]) -> dict[str, Any]:
    return state


def report(state: dict[str, Any]) -> dict[str, Any]:
    return state


def index_document(state: dict[str, Any]) -> dict[str, Any]:
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
