from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from html import escape
from typing import Any


def combine_validation_status(*results: dict[str, Any] | None) -> str:
    statuses = []
    for item in results:
        if not item:
            continue
        status = str(item.get("validation_status", "passed"))
        statuses.append(status)

    if "failed" in statuses:
        return "failed"
    if "partial" in statuses:
        return "partial"
    return "passed" if statuses else "passed"


def _recommendation_for(status: str, discrepancies: list[dict[str, Any]], rules: dict[str, Any] | None = None) -> str:
    if status == "passed":
        return "approve"

    high_count = sum(1 for record in discrepancies if str(record.get("severity", "")).lower() == "high")
    po_not_found = any("not found" in str(record.get("message", "")).lower() for record in discrepancies)
    threshold = 3
    if rules:
        threshold = int(rules.get("recommendation", {}).get("reject_if_high_count_gte", threshold))

    if high_count >= threshold or po_not_found:
        return "reject"
    return "review"


def build_report(
    invoice: dict[str, Any],
    internal_validation: dict[str, Any] | None,
    erp_validation: dict[str, Any] | None,
    source_language: str | None = None,
    translation_confidence: float | None = None,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    internal_discrepancies = list((internal_validation or {}).get("discrepancies", []))
    erp_discrepancies = list((erp_validation or {}).get("discrepancies", []))
    all_discrepancies = internal_discrepancies + erp_discrepancies
    severity_counts = Counter(str(item.get("severity", "low")).lower() for item in all_discrepancies)
    source_counts = Counter(str(item.get("source", "internal")).lower() for item in all_discrepancies)
    missing_fields = sorted(
        {
            field
            for validation in (internal_validation, erp_validation)
            for field in list((validation or {}).get("missing_fields", []))
        }
    )

    status = combine_validation_status(internal_validation, erp_validation)
    recommendation = _recommendation_for(status, all_discrepancies, rules)
    report = {
        "invoice_summary": {
            "invoice_number": invoice.get("invoice_number"),
            "vendor_name": invoice.get("vendor_name"),
            "currency": invoice.get("currency"),
            "total_amount": invoice.get("total_amount"),
            "po_number": invoice.get("po_number"),
        },
        "validation_status": status,
        "recommendation": recommendation,
        "missing_fields": missing_fields,
        "discrepancy_summary": {
            "total": len(all_discrepancies),
            "by_severity": dict(severity_counts),
            "by_source": dict(source_counts),
            "items": all_discrepancies,
        },
        "translation_summary": {
            "language": source_language,
            "confidence": translation_confidence,
            "translated": source_language not in (None, "", "en") if source_language else True,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return report


def render_html_report(report: dict[str, Any]) -> str:
    summary = report.get("invoice_summary", {})
    discrepancy_summary = report.get("discrepancy_summary", {})
    items = discrepancy_summary.get("items", [])
    body_rows = []
    for item in items:
        body_rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('severity', 'low')))}</td>"
            f"<td>{escape(str(item.get('field_name', 'n/a')))}</td>"
            f"<td>{escape(str(item.get('invoice_value', '')))}</td>"
            f"<td>{escape(str(item.get('expected_value', '')))}</td>"
            f"<td>{escape(str(item.get('deviation_pct', '')))}</td>"
            "</tr>"
        )
    if not body_rows:
        body_rows.append("<tr><td colspan='5'>No discrepancies</td></tr>")

    return f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Invoice Audit Report</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }}
          .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; background: #eef2ff; }}
          table {{ border-collapse: collapse; width: 100%; margin-top: 18px; }}
          th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
          th {{ background: #f3f4f6; }}
        </style>
      </head>
      <body>
        <h1>Invoice audit report</h1>
        <p><strong>Invoice:</strong> {escape(str(summary.get('invoice_number', 'n/a')))}</p>
        <p><strong>Vendor:</strong> {escape(str(summary.get('vendor_name', 'n/a')))}</p>
        <p><strong>Status:</strong> <span class='badge'>{escape(str(report.get('validation_status', 'unknown')))}</span></p>
        <p><strong>Recommendation:</strong> {escape(str(report.get('recommendation', 'review')))}</p>
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>Field</th>
              <th>Invoice value</th>
              <th>Expected value</th>
              <th>Deviation %</th>
            </tr>
          </thead>
          <tbody>
            {''.join(body_rows)}
          </tbody>
        </table>
      </body>
    </html>
    """


def report_to_text(report: dict[str, Any]) -> str:
    summary = report.get("invoice_summary", {})
    status = report.get("validation_status", "unknown")
    recommendation = report.get("recommendation", "review")
    return (
        f"Invoice {summary.get('invoice_number', 'n/a')} for {summary.get('vendor_name', 'n/a')} "
        f"has validation status {status} and recommendation {recommendation}."
    )
