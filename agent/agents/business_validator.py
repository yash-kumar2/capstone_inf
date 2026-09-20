from __future__ import annotations

import re
from decimal import Decimal
from difflib import SequenceMatcher

from ..tools.erp_tools import ErpUnavailable


def _to_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _normalize_vendor_name(name: str) -> str:
    if not name:
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", " ", name.lower())
    cleaned = re.sub(r"\b(ltd|limited|inc|llc|gmbh|sa|sarl|corp|company)\b", " ", cleaned)
    return " ".join(cleaned.split())


def _severity_for_deviation(deviation_pct: Decimal | None, severity_map: dict, default: str = "low") -> str:
    if deviation_pct is None:
        return default
    medium_from = _to_decimal(severity_map.get("medium_from_pct", Decimal("5"))) or Decimal("5")
    high_from = _to_decimal(severity_map.get("high_from_pct", Decimal("10"))) or Decimal("10")
    if deviation_pct >= high_from:
        return "high"
    if deviation_pct >= medium_from:
        return "medium"
    return "low"


def _canonical_invoice(invoice: dict) -> dict:
    if not isinstance(invoice, dict):
        return {}
    normalized = dict(invoice)
    aliases = {
        "invoice_no": "invoice_number",
        "invoice_num": "invoice_number",
        "vendor_id": "vendor_name",
        "vendor": "vendor_name",
        "total": "total_amount",
        "total_due": "total_amount",
        "gross_total": "total_amount",
        "sku": "item_code",
        "item_no": "item_code",
    }
    for alias, target in aliases.items():
        if alias in normalized and target not in normalized:
            normalized[target] = normalized[alias]
    return normalized


def business_validate(invoice: dict, line_items: list[dict], rules: dict, erp_client) -> dict:
    invoice = _canonical_invoice(invoice)
    discrepancies: list[dict] = []
    po_number = invoice.get("po_number")
    if not po_number:
        discrepancies.append({
            "source": "erp",
            "line_number": None,
            "field_name": "po_number",
            "invoice_value": None,
            "expected_value": "required",
            "deviation_pct": None,
            "severity": "high",
            "message": "PO number is missing",
        })
        return {"validation_status": "failed", "discrepancies": discrepancies, "missing_fields": ["po_number"]}

    try:
        po = erp_client.get_po(po_number)
    except ErpUnavailable:
        return {"validation_status": "failed", "discrepancies": [{
            "source": "erp",
            "line_number": None,
            "field_name": "po_number",
            "invoice_value": po_number,
            "expected_value": "PO exists",
            "deviation_pct": None,
            "severity": "high",
            "message": "PO not found",
        }], "missing_fields": []}

    if po is None:
        discrepancies.append({
            "source": "erp",
            "line_number": None,
            "field_name": "po_number",
            "invoice_value": po_number,
            "expected_value": "PO exists",
            "deviation_pct": None,
            "severity": "high",
            "message": "PO not found",
        })
        return {"validation_status": "failed", "discrepancies": discrepancies, "missing_fields": []}

    vendor_id = po.get("vendor_id")
    if vendor_id:
        vendor = erp_client.get_vendor(vendor_id)
        if vendor:
            invoice_vendor = _normalize_vendor_name(invoice.get("vendor_name", ""))
            erp_vendor = _normalize_vendor_name(vendor.get("name", ""))
            ratio = SequenceMatcher(None, invoice_vendor, erp_vendor).ratio()
            accept = _to_decimal(rules.get("erp", {}).get("vendor_match", {}).get("accept", Decimal("0.92"))) or Decimal("0.92")
            reject = _to_decimal(rules.get("erp", {}).get("vendor_match", {}).get("reject", Decimal("0.60"))) or Decimal("0.60")
            if ratio < reject:
                discrepancies.append({
                    "source": "erp",
                    "line_number": None,
                    "field_name": "vendor_name",
                    "invoice_value": invoice.get("vendor_name"),
                    "expected_value": vendor.get("name"),
                    "deviation_pct": Decimal(str((1 - ratio) * 100)),
                    "severity": "high",
                    "message": "Vendor name does not match ERP record",
                })
    if invoice.get("currency") != po.get("currency"):
        discrepancies.append({
            "source": "erp",
            "line_number": None,
            "field_name": "currency",
            "invoice_value": invoice.get("currency"),
            "expected_value": po.get("currency"),
            "deviation_pct": None,
            "severity": "medium",
            "message": "Currency mismatch with ERP",
        })

    po_lines = {str(item.get("sku", "")).strip(): item for item in po.get("line_items", [])}
    item_lookup = {str(item.get("line_number")): item for item in po.get("line_items", [])}

    for line in line_items:
        invoice_item_code = str(line.get("item_code", "")).strip()
        po_line = po_lines.get(invoice_item_code) or item_lookup.get(str(line.get("line_number")))
        if po_line is None:
            discrepancies.append({
                "source": "erp",
                "line_number": line.get("line_number"),
                "field_name": "item_code",
                "invoice_value": invoice_item_code,
                "expected_value": "matching ERP line",
                "deviation_pct": None,
                "severity": "high",
                "message": "Invoice line does not match ERP PO line",
            })
            continue

        quantity = _to_decimal(line.get("quantity"))
        unit_price = _to_decimal(line.get("unit_price"))
        po_quantity = _to_decimal(po_line.get("quantity"))
        po_price = _to_decimal(po_line.get("unit_price"))
        qty_tol = _to_decimal(rules.get("erp", {}).get("quantity_tolerance_pct", Decimal("0"))) or Decimal("0")
        price_tol = _to_decimal(rules.get("erp", {}).get("unit_price_tolerance_pct", Decimal("5"))) or Decimal("5")

        if quantity is not None and po_quantity is not None and po_quantity != 0:
            deviation = abs(quantity - po_quantity) / po_quantity * Decimal("100")
            if deviation > qty_tol:
                discrepancies.append({
                    "source": "erp",
                    "line_number": line.get("line_number"),
                    "field_name": "quantity",
                    "invoice_value": str(quantity),
                    "expected_value": str(po_quantity),
                    "deviation_pct": deviation,
                    "severity": _severity_for_deviation(deviation, rules.get("severity", {})),
                    "message": "Quantity differs from PO",
                })

        if unit_price is not None and po_price is not None and po_price != 0:
            deviation = abs(unit_price - po_price) / po_price * Decimal("100")
            if deviation > price_tol:
                discrepancies.append({
                    "source": "erp",
                    "line_number": line.get("line_number"),
                    "field_name": "unit_price",
                    "invoice_value": str(unit_price),
                    "expected_value": str(po_price),
                    "deviation_pct": deviation,
                    "severity": _severity_for_deviation(deviation, rules.get("severity", {})),
                    "message": "Unit price differs from PO",
                })

    validation_status = "passed" if not discrepancies else "failed"
    return {"validation_status": validation_status, "discrepancies": discrepancies, "missing_fields": []}
