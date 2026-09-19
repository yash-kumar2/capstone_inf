from __future__ import annotations

from pathlib import Path

from ..tools.extraction_tools import extract_docx, extract_image, extract_pdf


def extract_invoice(file_path: str, file_type: str, min_chars_per_page: int = 40) -> tuple[str, str]:
    if file_type == "pdf":
        return extract_pdf(file_path, min_chars_per_page=min_chars_per_page)
    if file_type == "docx":
        return extract_docx(file_path)
    if file_type == "png":
        return extract_image(file_path)
    raise ValueError(f"Unsupported file type: {file_type}")
