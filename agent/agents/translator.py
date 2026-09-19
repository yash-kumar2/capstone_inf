from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation

from ..cache import cache_get, cache_set
from ..llm import chat


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean_text(value: str) -> str:
    return (value or "").replace("\r\n", "\n").replace("\r", "\n").replace("\0", "")


def detect_language(text: str, model: str | None = None) -> tuple[str, float]:
    snippet = (text or "")[:1500]
    cache_key = f"lang:{_hash(snippet)}"
    cached = cache_get(cache_key)
    if cached is not None:
        if isinstance(cached, dict):
            return str(cached.get("language", "en")), float(cached.get("confidence", 1.0))
        if isinstance(cached, tuple):
            return str(cached[0]), float(cached[1])

    model_name = model or "bedrock/amazon.nova-lite-v1:0"
    try:
        payload = chat(
            model_name,
            [{"role": "user", "content": "Return only JSON {\"language\": \"ISO-639-1\", \"confidence\": 0.0-1.0}\nDetect the source language of this invoice text.\n\n" + snippet}],
            temperature=0,
            json=True,
            cache=True,
        )
        data = json.loads(payload)
        language = str(data.get("language", "en")).lower()
        confidence = float(data.get("confidence", 1.0))
    except Exception:
        language = "en"
        confidence = 1.0

    cache_set(cache_key, {"language": language, "confidence": confidence})
    return language, confidence


def translate_text(source_text: str, source_language: str, model: str | None = None) -> tuple[str, float]:
    text = _clean_text(source_text)
    if (source_language or "").lower() in {"en", "eng", "english", ""}:
        return text, 1.0

    cache_key = f"translation:{_hash(text)}"
    cached = cache_get(cache_key)
    if cached is not None:
        if isinstance(cached, dict):
            return str(cached.get("translated_text", text)), float(cached.get("confidence", 1.0))
        if isinstance(cached, tuple):
            return str(cached[0]), float(cached[1])

    model_name = model or "bedrock/cohere.command-r-plus-v1:0"
    try:
        response = chat(
            model_name,
            [{
                "role": "user",
                "content": (
                    "Translate the invoice text to English. Do not alter numbers, dates, currency symbols, codes, or line breaks. "
                    "Return the translation wrapped in <translation>...</translation><confidence>0.93</confidence>.\n\n" + text
                ),
            }],
            temperature=0,
            json=False,
            cache=True,
        )
        match = re.search(r"<translation>(.*?)</translation>\s*<confidence>(.*?)</confidence>", response, re.S | re.I)
        if match:
            translated = match.group(1).strip()
            confidence = float(match.group(2).strip())
        else:
            translated = response.strip()
            confidence = 0.9
    except Exception:
        translated = text
        confidence = 1.0

    cache_set(cache_key, {"translated_text": translated, "confidence": confidence})
    return translated, confidence


def _to_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(" ", "").replace(".", "").replace(",", ".") if "," in str(value) and "." not in str(value) else str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _currency_from_symbol(symbol: str) -> str | None:
    mapping = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY"}
    return mapping.get(symbol)


def _parse_iso_date(value: str, date_order: str = "DMY") -> str | None:
    if not value:
        return None
    match = re.search(r"(\d{1,2})[^\d](\d{1,2})[^\d](\d{2,4})", value)
    if not match:
        return None
    d, m, y = match.groups()
    if len(y) == 2:
        y = "20" + y if int(y) <= 25 else "19" + y
    try:
        from datetime import datetime
        dt = datetime.strptime(f"{d}/{m}/{y}", "%d/%m/%Y") if date_order.upper() == "DMY" else datetime.strptime(f"{m}/{d}/{y}", "%m/%d/%Y")
        return dt.date().isoformat()
    except ValueError:
        return None


def parse_fields(translated_text: str, source_language: str) -> tuple[dict, list[dict]]:
    text = _clean_text(translated_text)
    invoice: dict = {}
    line_items: list[dict] = []

    invoice_number_match = re.search(r"(?:invoice(?:\s*(?:no|number)|\s*#)?\s*[:#-]?\s*)([A-Z0-9-]+)", text, re.I)
    if invoice_number_match:
        invoice["invoice_number"] = invoice_number_match.group(1).strip()

    for key in ["invoice_date", "date"]:
        date_match = re.search(r"(?:invoice date|date)\s*[:#-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text, re.I)
        if date_match:
            invoice["invoice_date"] = _parse_iso_date(date_match.group(1), "DMY")
            break

    vendor_match = re.search(r"(?:vendor|supplier)\s*[:#-]?\s*([A-Za-z0-9 .&'-]+)", text, re.I)
    if vendor_match:
        invoice["vendor_name"] = vendor_match.group(1).strip()

    po_match = re.search(r"(?:po\s*(?:no|number)|purchase order)\s*[:#-]?\s*([A-Z0-9-]+)", text, re.I)
    if po_match:
        invoice["po_number"] = po_match.group(1).strip()

    currency_match = re.search(r"\b(USD|EUR|GBP|INR|JPY|AUD|CAD)\b", text, re.I)
    if currency_match:
        invoice["currency"] = currency_match.group(1).upper()
    elif re.search(r"\$", text):
        invoice["currency"] = "USD"
    elif re.search(r"€", text):
        invoice["currency"] = "EUR"
    elif re.search(r"₹", text):
        invoice["currency"] = "INR"

    total_match = re.search(r"(?:grand total|total due|total)\s*[:#-]?\s*([\$€£₹¥]?\s*\d[\d,]*\.?\d{0,2})", text, re.I)
    if total_match:
        value = total_match.group(1).strip()
        invoice["total_amount"] = _to_decimal(value)

    subtotal_match = re.search(r"(?:subtotal|sub total)\s*[:#-]?\s*([\$€£₹¥]?\s*\d[\d,]*\.?\d{0,2})", text, re.I)
    if subtotal_match:
        value = subtotal_match.group(1).strip()
        invoice["subtotal"] = _to_decimal(value)

    tax_match = re.search(r"(?:tax|vat|gst)\s*[:#-]?\s*([\$€£₹¥]?\s*\d[\d,]*\.?\d{0,2})", text, re.I)
    if tax_match:
        value = tax_match.group(1).strip()
        invoice["tax_amount"] = _to_decimal(value)

    for line in re.finditer(r"(?m)^(?:\d+\s+)?([^\n]+)$", text):
        raw = line.group(1)
        if not raw or len(raw) < 8:
            continue
        if any(token in raw.lower() for token in ["invoice", "total", "subtotal", "tax", "vendor", "date"]):
            continue
        parts = [p.strip() for p in re.split(r"\s{2,}|\t|\|", raw)]
        if len(parts) >= 4:
            item_code = parts[0]
            qty = _to_decimal(parts[-3]) if len(parts) >= 4 else None
            unit_price = _to_decimal(parts[-2]) if len(parts) >= 4 else None
            line_total = _to_decimal(parts[-1]) if len(parts) >= 4 else None
            if item_code and (qty is not None or unit_price is not None or line_total is not None):
                line_items.append({
                    "line_number": len(line_items) + 1,
                    "item_code": item_code,
                    "description": " ".join(parts[1:-3]) or item_code,
                    "quantity": qty or Decimal("0"),
                    "unit_price": unit_price or Decimal("0"),
                    "line_total": line_total or Decimal("0"),
                })

    return invoice, line_items
