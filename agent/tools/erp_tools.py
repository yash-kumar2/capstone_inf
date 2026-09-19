from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx


class ErpUnavailable(RuntimeError):
    pass


class ErpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=5.0)

    def _request_json(self, path: str) -> Any:
        try:
            response = self.client.get(path)
            if response.status_code == 404:
                return None
            if response.is_error:
                raise ErpUnavailable(f"ERP request failed: {response.status_code}")
            return response.json(parse_float=Decimal)
        except httpx.HTTPError as exc:  # pragma: no cover - network errors
            raise ErpUnavailable(str(exc)) from exc

    def get_po(self, po_number: str):
        return self._request_json(f"/po/{po_number}")

    def get_vendor(self, vendor_id: str):
        return self._request_json(f"/vendor/{vendor_id}")

    def get_sku(self, sku_code: str):
        return self._request_json(f"/sku/{sku_code}")

    def close(self) -> None:
        self.client.close()
