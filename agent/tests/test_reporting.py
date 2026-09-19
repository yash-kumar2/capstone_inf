from agent.agents.reporter import build_report, combine_validation_status


def test_combine_validation_status_uses_failures_first():
    assert combine_validation_status({"validation_status": "passed"}, {"validation_status": "partial"}) == "partial"
    assert combine_validation_status({"validation_status": "failed"}, {"validation_status": "passed"}) == "failed"
    assert combine_validation_status({"validation_status": "passed"}, {"validation_status": "passed"}) == "passed"


def test_build_report_uses_structured_summary_and_recommendation():
    report = build_report(
        invoice={"invoice_number": "INV-102", "vendor_name": "Acme", "currency": "USD"},
        internal_validation={"validation_status": "partial", "missing_fields": ["invoice_date"], "discrepancies": [{"source": "internal", "severity": "high", "field_name": "invoice_date", "message": "Missing required field: invoice_date"}]},
        erp_validation={"validation_status": "failed", "discrepancies": [{"source": "erp", "severity": "medium", "field_name": "unit_price", "message": "Unit price differs from PO"}]},
        source_language="es",
        translation_confidence=0.87,
    )

    assert report["validation_status"] == "failed"
    assert report["recommendation"] in {"reject", "review", "approve"}
    assert report["discrepancy_summary"]["by_severity"]["high"] >= 1
    assert report["translation_summary"]["language"] == "es"
    assert "invoice_number" in report["invoice_summary"]
