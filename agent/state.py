from typing import TypedDict


class InvoiceState(TypedDict, total=False):
    invoice_id: str
    thread_id: str
    file_path: str
    file_name: str
    file_type: str
    file_checksum: str
    raw_extracted_text: str
    extraction_method: str
    source_language: str
    translated_text: str
    translation_confidence: float
    invoice: dict
    line_items: list[dict]
    internal_validation: dict
    erp_validation: dict
    validation_status: str
    report: dict
    recommendation: str
    duplicate: bool
    error: str | None
