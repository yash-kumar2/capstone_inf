from decimal import Decimal

from agent.agents.invoice_validator import validate_invoice


RULES = {
    "required_fields": {
        "header": ["invoice_no", "invoice_date", "vendor_id", "currency", "total_amount"],
        "line_item": ["item_code", "quantity", "unit_price", "line_total"],
    },
    "extraction": {"min_text_chars_per_page": 40},
    "parsing": {"date_order": "DMY", "labels": {"invoice_number": ["invoice no"], "total": ["total"]}},
    "arithmetic": {"line_total_tolerance_abs": Decimal("0.01"), "sum_tolerance_abs": Decimal("0.01")},
    "tax": {
        "required": False,
        "default_rate_pct": Decimal("18"),
        "rate_pct_by_currency": {"EUR": Decimal("19"), "INR": Decimal("18")},
        "tolerance_abs": Decimal("0.05"),
    },
    "erp": {
        "unit_price_tolerance_pct": Decimal("5"),
        "quantity_tolerance_pct": Decimal("0"),
        "currency_must_match": True,
        "vendor_match": {"accept": Decimal("0.92"), "reject": Decimal("0.60")},
    },
    "severity": {"medium_from_pct": Decimal("5"), "high_from_pct": Decimal("10"), "missing_field": "high", "po_not_found": "high"},
    "recommendation": {"reject_if_high_count_gte": 3, "reject_if_po_not_found": True},
}


def test_clean_pass():
    invoice = {
        "invoice_number": "INV-100",
        "invoice_date": "2026-09-19",
        "vendor_name": "Acme Supplies",
        "currency": "USD",
        "subtotal": Decimal("500.00"),
        "tax_amount": Decimal("90.00"),
        "total_amount": Decimal("590.00"),
    }
    line_items = [{"line_number": 1, "item_code": "SKU-001", "quantity": Decimal("10"), "unit_price": Decimal("50.00"), "line_total": Decimal("500.00") }]

    result = validate_invoice(invoice, line_items, RULES)

    assert result["validation_status"] == "passed"
    assert result["discrepancies"] == []
    assert result["missing_fields"] == []


def test_total_mismatch_high():
    invoice = {
        "invoice_number": "INV-200",
        "invoice_date": "2026-09-19",
        "vendor_name": "Acme Supplies",
        "currency": "USD",
        "subtotal": Decimal("500.00"),
        "tax_amount": Decimal("0.00"),
        "total_amount": Decimal("600.00"),
    }
    line_items = [{"line_number": 1, "item_code": "SKU-001", "quantity": Decimal("10"), "unit_price": Decimal("50.00"), "line_total": Decimal("500.00") }]

    result = validate_invoice(invoice, line_items, RULES)

    assert result["validation_status"] == "failed"
    assert any(d["field_name"] == "total_amount" for d in result["discrepancies"])
    assert any(d["severity"] == "high" for d in result["discrepancies"])


def test_wrong_tax():
    invoice = {
        "invoice_number": "INV-300",
        "invoice_date": "2026-09-19",
        "vendor_name": "Acme Supplies",
        "currency": "EUR",
        "subtotal": Decimal("100.00"),
        "tax_amount": Decimal("5.00"),
        "total_amount": Decimal("105.00"),
    }
    line_items = [{"line_number": 1, "item_code": "SKU-003", "quantity": Decimal("1"), "unit_price": Decimal("100.00"), "line_total": Decimal("100.00") }]

    result = validate_invoice(invoice, line_items, RULES)

    assert any(d["field_name"] == "tax_amount" for d in result["discrepancies"])


def test_missing_field():
    invoice = {
        "invoice_number": "INV-400",
        "invoice_date": "2026-09-19",
        "vendor_name": "Acme Supplies",
        "currency": "USD",
        "total_amount": Decimal("100.00"),
    }
    result = validate_invoice(invoice, [], RULES)

    assert "subtotal" in result["missing_fields"]
    assert result["validation_status"] == "partial"


def test_rounding_zero_point_zero_zero_five():
    invoice = {
        "invoice_number": "INV-500",
        "invoice_date": "2026-09-19",
        "vendor_name": "Acme Supplies",
        "currency": "USD",
        "subtotal": Decimal("0.01"),
        "tax_amount": Decimal("0.00"),
        "total_amount": Decimal("0.01"),
    }
    line_items = [{"line_number": 1, "item_code": "SKU-001", "quantity": Decimal("1"), "unit_price": Decimal("0.01"), "line_total": Decimal("0.01") }]

    result = validate_invoice(invoice, line_items, RULES)

    assert result["validation_status"] in {"passed", "partial"}


def test_custom_nested_schema_aliases_are_accepted():
    custom_rules = {
        "required_fields": {
            "header": ["invoice_no", "invoice_date", "vendor_id", "currency", "total_amount"],
            "line_item": ["sku", "quantity", "unit_price"],
        },
        "arithmetic": {"line_total_tolerance_abs": Decimal("0.01"), "sum_tolerance_abs": Decimal("0.01")},
        "tax": {
            "required": False,
            "default_rate_pct": Decimal("18"),
            "rate_pct_by_currency": {"EUR": Decimal("19"), "INR": Decimal("18")},
            "tolerance_abs": Decimal("0.05"),
        },
        "erp": {
            "unit_price_tolerance_pct": Decimal("5"),
            "quantity_tolerance_pct": Decimal("0"),
            "currency_must_match": True,
            "vendor_match": {"accept": Decimal("0.92"), "reject": Decimal("0.60")},
        },
        "severity": {"medium_from_pct": Decimal("5"), "high_from_pct": Decimal("10"), "missing_field": "high"},
        "recommendation": {"reject_if_high_count_gte": 3, "reject_if_po_not_found": True},
    }
    invoice = {
        "invoice_no": "INV-900",
        "invoice_date": "2026-09-19",
        "vendor_id": "V-001",
        "currency": "USD",
        "subtotal": Decimal("100.00"),
        "tax_amount": Decimal("18.00"),
        "total_amount": Decimal("118.00"),
    }
    line_items = [{"line_number": 1, "sku": "SKU-001", "quantity": Decimal("2"), "unit_price": Decimal("50.00"), "line_total": Decimal("100.00") }]

    result = validate_invoice(invoice, line_items, custom_rules)

    assert result["validation_status"] == "passed"
    assert result["missing_fields"] == []
    assert result["discrepancies"] == []
