from agent.db import get_effective_invoice


def test_effective_invoice_uses_latest_feedback_for_overlay():
    invoice = {
        "invoice_id": "00000000-0000-0000-0000-000000000001",
        "invoice_number": "INV-100",
        "vendor_name": "Acme",
        "currency": "USD",
        "total_amount": 1000,
    }
    line_items = [{"invoice_id": "00000000-0000-0000-0000-000000000001", "line_number": 1, "unit_price": 500}]

    result = get_effective_invoice(invoice, line_items, [{"field_name": "line_items[1].unit_price", "corrected_value": "480", "corrected_at": "2026-09-19T00:00:00+00:00"}])
    assert result["line_items"][0]["unit_price"] == 480
    assert result["invoice_number"] == "INV-100"
