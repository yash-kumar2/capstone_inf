from __future__ import annotations

import os
from pathlib import Path

from docx import Document
from PIL import Image
from pdf2image import convert_from_path
import pdfplumber
import pytesseract


def _normalize_newlines(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\0", "")


def extract_pdf(path: str, min_chars_per_page: int = 40) -> tuple[str, str]:
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(_normalize_newlines(text))

    text = "\n\n".join(pages)
    if len("".join(ch for ch in text if not ch.isspace())) >= max(1, min_chars_per_page * max(1, len(pages))):
        return text, "pdfplumber"

    ocr_pages: list[str] = []
    images = convert_from_path(path, dpi=300)
    for image in images:
        ocr_pages.append(_normalize_newlines(pytesseract.image_to_string(image, lang=os.getenv("OCR_LANGS", "eng+spa+deu+fra"))))
    return "\n\n".join(ocr_pages), "tesseract"


def extract_docx(path: str) -> tuple[str, str]:
    doc = Document(path)
    chunks: list[str] = []
    for element in doc.iter_inner_content():
        if hasattr(element, "text"):
            text = _normalize_newlines(element.text)
            if text:
                chunks.append(text)
        elif hasattr(element, "rows"):
            for row in element.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
                if cells:
                    chunks.append(" | ".join(cells))
    return "\n".join(chunks), "docx"


def extract_image(path: str) -> tuple[str, str]:
    image = Image.open(path).convert("L")
    width, height = image.size
    if width < 1500:
        image = image.resize((width * 2, height * 2))
    text = pytesseract.image_to_string(image, config="--psm 6", lang=os.getenv("OCR_LANGS", "eng+spa+deu+fra"))
    return _normalize_newlines(text), "tesseract"
