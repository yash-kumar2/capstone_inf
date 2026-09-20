from decimal import Decimal

from agent.agents.business_validator import business_validate
from agent.tools.erp_tools import ErpClient


RULES = {
    "required_fields": {
        "header": ["invoice_no", "invoice_date", "vendor_id", "currency", "total_amount"],
        "line_item": ["item_code", "quantity", "unit_price"],
    },
    "erp": {
        "unit_price_tolerance_pct": Decimal("5"),
        "quantity_tolerance_pct": Decimal("0"),
        "currency_must_match": True,
        "vendor_match": {"accept": Decimal("0.92"), "reject": Decimal("0.60")},
    },
    "severity": {"medium_from_pct": Decimal("5"), "high_from_pct": Decimal("10")},
}


class DummyClient:
    def __init__(self, po_payload):
        self.po_payload = po_payload

    def get_po(self, po_number):
        return self.po_payload

    def get_vendor(self, vendor_id):
        return {"vendor_id": vendor_id, "name": "Acme Supplies Ltd"}


def test_business_validate_clean_pass():
    invoice = {"po_number": "PO-1001", "vendor_name": "Acme Supplies Ltd", "currency": "USD"}
    line_items = [{"line_number": 1, "item_code": "SKU-001", "quantity": Decimal("2"), "unit_price": Decimal("120.00")}]
    result = business_validate(invoice, line_items, RULES, DummyClient({"vendor_id": "V001", "currency": "USD", "line_items": [{"sku": "SKU-001", "quantity": Decimal("2"), "unit_price": Decimal("120.00"), "line_number": 1}] }))
    assert result["validation_status"] == "passed"


def test_business_validate_exact_5_percent_passes():
    invoice = {"po_number": "PO-1001", "vendor_name": "Acme Supplies Ltd", "currency": "USD"}
    line_items = [{"line_number": 1, "item_code": "SKU-001", "quantity": Decimal("2"), "unit_price": Decimal("126.00")}]
    result = business_validate(invoice, line_items, RULES, DummyClient({"vendor_id": "V001", "currency": "USD", "line_items": [{"sku": "SKU-001", "quantity": Decimal("2"), "unit_price": Decimal("120.00"), "line_number": 1}] }))
    assert result["validation_status"] == "passed"


def test_business_validate_5_01_percent_fails():
    invoice = {"po_number": "PO-1001", "vendor_name": "Acme Supplies Ltd", "currency": "USD"}
    line_items = [{"line_number": 1, "item_code": "SKU-001", "quantity": Decimal("2"), "unit_price": Decimal("126.10")}]
    result = business_validate(invoice, line_items, RULES, DummyClient({"vendor_id": "V001", "currency": "USD", "line_items": [{"sku": "SKU-001", "quantity": Decimal("2"), "unit_price": Decimal("120.00"), "line_number": 1}] }))
    assert result["validation_status"] == "failed"
    assert any(d["field_name"] == "unit_price" for d in result["discrepancies"])


def test_business_validate_missing_po_is_failed():
    result = business_validate({"vendor_name": "Acme Supplies Ltd", "currency": "USD"}, [], RULES, DummyClient({}))
    assert result["validation_status"] == "failed"
    assert result["discrepancies"][0]["field_name"] == "po_number"


def test_business_validate_quantity_mismatch():
    invoice = {"po_number": "PO-1001", "vendor_name": "Acme Supplies Ltd", "currency": "USD"}
    line_items = [{"line_number": 1, "item_code": "SKU-001", "quantity": Decimal("3"), "unit_price": Decimal("120.00")}]
    result = business_validate(invoice, line_items, RULES, DummyClient({"vendor_id": "V001", "currency": "USD", "line_items": [{"sku": "SKU-001", "quantity": Decimal("2"), "unit_price": Decimal("120.00"), "line_number": 1}] }))
    assert any(d["field_name"] == "quantity" for d in result["discrepancies"])
