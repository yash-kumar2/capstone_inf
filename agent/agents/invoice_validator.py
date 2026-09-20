from __future__ import annotations

from decimal import Decimal, InvalidOperation


FIELD_ALIASES = {
    "invoice_no": "invoice_number",
    "invoice_num": "invoice_number",
    "invoice_id": "invoice_number",
    "vendor_id": "vendor_name",
    "vendor": "vendor_name",
    "total": "total_amount",
    "total_due": "total_amount",
    "gross_total": "total_amount",
    "sku": "item_code",
    "item_no": "item_code",
    "line_item_total": "line_total",
}


def _flatten_required_fields(required_fields):
    if isinstance(required_fields, dict):
        flattened = []
        for value in required_fields.values():
            if isinstance(value, (list, tuple, set)):
                flattened.extend(value)
            elif isinstance(value, str):
                flattened.append(value)
        return flattened
    if isinstance(required_fields, (list, tuple, set)):
        return list(required_fields)
    if required_fields is None:
        return []
    return [required_fields]


def _split_required_fields(rules: dict) -> tuple[list[str], list[str]]:
    required_fields = rules.get("required_fields", [])
    if isinstance(required_fields, dict):
        header_fields = _flatten_required_fields(required_fields.get("header", []) or required_fields.get("invoice", []) or [])
        line_fields = _flatten_required_fields(required_fields.get("line_item", []) or required_fields.get("items", []) or [])
        return header_fields, line_fields
    return _flatten_required_fields(required_fields), []


def _canonicalize_invoice(invoice: dict) -> dict:
    canonical = dict(invoice or {})
    for alias, target in FIELD_ALIASES.items():
        if alias in canonical and target not in canonical:
            canonical[target] = canonical[alias]
    return canonical


def _canonicalize_line_items(line_items: list[dict]) -> list[dict]:
    canonical_items = []
    for line in (line_items or []):
        if not isinstance(line, dict):
            canonical_items.append(line)
            continue
        normalized = dict(line)
        for alias, target in FIELD_ALIASES.items():
            if alias in normalized and target not in normalized:
                normalized[target] = normalized[alias]
        canonical_items.append(normalized)
    return canonical_items


def to_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def safe_divide(numerator, denominator):
    if denominator in (None, Decimal("0")):
        return None
    return numerator / denominator


def _severity_for_deviation(deviation_pct, rules):
    if deviation_pct is None:
        return "low"
    medium_from = to_decimal(rules.get("severity", {}).get("medium_from_pct", Decimal("5")))
    high_from = to_decimal(rules.get("severity", {}).get("high_from_pct", Decimal("10")))
    if deviation_pct >= high_from:
        return "high"
    if deviation_pct >= medium_from:
        return "medium"
    return "low"


def validate_invoice(invoice: dict, line_items: list[dict], rules: dict) -> dict:
    invoice = _canonicalize_invoice(invoice)
    line_items = _canonicalize_line_items(line_items)
    discrepancies: list[dict] = []
    missing_fields: list[str] = []
    required_fields, line_required_fields = _split_required_fields(rules)

    for field in required_fields:
        canonical_field = FIELD_ALIASES.get(field, field)
        value = invoice.get(field) if field in invoice else invoice.get(canonical_field)
        if value in (None, ""):
            missing_fields.append(field)
            discrepancies.append({
                "source": "internal",
                "line_number": None,
                "field_name": field,
                "invoice_value": None,
                "expected_value": "required",
                "deviation_pct": None,
                "severity": rules.get("severity", {}).get("missing_field", "high"),
                "message": f"Missing required field: {field}",
            })

    for field in line_required_fields:
        for line in line_items:
            canonical_field = FIELD_ALIASES.get(field, field)
            value = line.get(field) if field in line else line.get(canonical_field)
            if value in (None, ""):
                missing_fields.append(field)
                discrepancies.append({
                    "source": "internal",
                    "line_number": line.get("line_number"),
                    "field_name": field,
                    "invoice_value": None,
                    "expected_value": "required",
                    "deviation_pct": None,
                    "severity": rules.get("severity", {}).get("missing_field", "high"),
                    "message": f"Missing required field: {field} on line {line.get('line_number')}",
                })
                break

    if "subtotal" not in invoice or invoice.get("subtotal") in (None, ""):
        if invoice.get("total_amount") is not None or invoice.get("tax_amount") is not None or line_items:
            if "subtotal" not in missing_fields:
                missing_fields.append("subtotal")
                discrepancies.append({
                    "source": "internal",
                    "line_number": None,
                    "field_name": "subtotal",
                    "invoice_value": None,
                    "expected_value": "required",
                    "deviation_pct": None,
                    "severity": rules.get("severity", {}).get("missing_field", "high"),
                    "message": "Missing required field: subtotal",
                })

    arithmetic_rules = rules.get("arithmetic", {})
    line_tol = to_decimal(arithmetic_rules.get("line_total_tolerance_abs", Decimal("0.01"))) or Decimal("0.01")
    sum_tol = to_decimal(arithmetic_rules.get("sum_tolerance_abs", Decimal("0.01"))) or Decimal("0.01")

    for line in line_items:
        line_number = line.get("line_number")
        quantity = to_decimal(line.get("quantity"))
        unit_price = to_decimal(line.get("unit_price"))
        line_total = to_decimal(line.get("line_total"))
        if quantity is not None and unit_price is not None and line_total is not None:
            expected = quantity * unit_price
            if abs(expected - line_total) > line_tol:
                deviation_pct = None
                if expected != 0:
                    deviation_pct = abs((line_total - expected) / expected) * Decimal("100")
                discrepancies.append({
                    "source": "internal",
                    "line_number": line_number,
                    "field_name": "line_total",
                    "invoice_value": str(line_total),
                    "expected_value": str(expected),
                    "deviation_pct": deviation_pct,
                    "severity": _severity_for_deviation(deviation_pct, rules) if deviation_pct is not None else "low",
                    "message": f"Line total mismatch on line {line_number}",
                })

    subtotal = to_decimal(invoice.get("subtotal"))
    total_amount = to_decimal(invoice.get("total_amount"))
    tax_amount = to_decimal(invoice.get("tax_amount"))
    if subtotal is not None and line_items:
        sum_line_totals = sum((to_decimal(item.get("line_total")) or Decimal("0") for item in line_items), Decimal("0"))
        if abs(sum_line_totals - subtotal) > sum_tol:
            deviation_pct = None
            if subtotal != 0:
                deviation_pct = abs((sum_line_totals - subtotal) / subtotal) * Decimal("100")
            discrepancies.append({
                "source": "internal",
                "line_number": None,
                "field_name": "subtotal",
                "invoice_value": str(subtotal),
                "expected_value": str(sum_line_totals),
                "deviation_pct": deviation_pct,
                "severity": _severity_for_deviation(deviation_pct, rules) if deviation_pct is not None else "low",
                "message": "Subtotal does not match line totals",
            })

    if tax_amount is not None and subtotal is not None:
        currency = str(invoice.get("currency", "")).upper()
        tax_rules = rules.get("tax", {})
        rate_map = tax_rules.get("rate_pct_by_currency", {})
        default_rate = to_decimal(tax_rules.get("default_rate_pct", Decimal("18"))) or Decimal("18")
        rate = to_decimal(rate_map.get(currency, default_rate)) or default_rate
        expected_tax = subtotal * (rate / Decimal("100"))
        tolerance = to_decimal(tax_rules.get("tolerance_abs", Decimal("0.05"))) or Decimal("0.05")
        if abs(expected_tax - tax_amount) > tolerance:
            deviation_pct = None
            if expected_tax != 0:
                deviation_pct = abs((tax_amount - expected_tax) / expected_tax) * Decimal("100")
            discrepancies.append({
                "source": "internal",
                "line_number": None,
                "field_name": "tax_amount",
                "invoice_value": str(tax_amount),
                "expected_value": str(expected_tax),
                "deviation_pct": deviation_pct,
                "severity": _severity_for_deviation(deviation_pct, rules) if deviation_pct is not None else "low",
                "message": "Tax amount does not match expected tax",
            })

    if total_amount is not None:
        if tax_amount is not None and subtotal is not None:
            expected_total = subtotal + tax_amount
            if abs(expected_total - total_amount) > sum_tol:
                deviation_pct = None
                if expected_total != 0:
                    deviation_pct = abs((total_amount - expected_total) / expected_total) * Decimal("100")
                discrepancies.append({
                    "source": "internal",
                    "line_number": None,
                    "field_name": "total_amount",
                    "invoice_value": str(total_amount),
                    "expected_value": str(expected_total),
                    "deviation_pct": deviation_pct,
                    "severity": _severity_for_deviation(deviation_pct, rules) if deviation_pct is not None else "low",
                    "message": "Total does not equal subtotal plus tax",
                })
        elif line_items:
            sum_line_totals = sum((to_decimal(item.get("line_total")) or Decimal("0") for item in line_items), Decimal("0"))
            if abs(sum_line_totals - total_amount) > sum_tol:
                deviation_pct = None
                if sum_line_totals != 0:
                    deviation_pct = abs((total_amount - sum_line_totals) / sum_line_totals) * Decimal("100")
                discrepancies.append({
                    "source": "internal",
                    "line_number": None,
                    "field_name": "total_amount",
                    "invoice_value": str(total_amount),
                    "expected_value": str(sum_line_totals),
                    "deviation_pct": deviation_pct,
                    "severity": _severity_for_deviation(deviation_pct, rules) if deviation_pct is not None else "low",
                    "message": "Total amount mismatch against line totals",
                })

    if discrepancies:
        missing_only = all(
            (d.get("field_name") in missing_fields) and (d.get("expected_value") == "required")
            for d in discrepancies
        )
        if missing_only:
            validation_status = "partial"
        else:
            validation_status = "failed"
    elif missing_fields:
        validation_status = "partial"
    else:
        validation_status = "passed"

    return {
        "validation_status": validation_status,
        "discrepancies": discrepancies,
        "missing_fields": missing_fields,
    }
