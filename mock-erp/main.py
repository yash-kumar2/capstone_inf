from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from .db import get_conn
from .models import PurchaseOrder, SkuItem, Vendor

app = FastAPI(title="Mock ERP")


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="ERP database unavailable")


@app.get("/vendor/{vendor_id}", response_model=Vendor)
def get_vendor(vendor_id: str) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT vendor_id, name, currency, status FROM erp.vendors WHERE vendor_id = %s",
                (vendor_id,),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="vendor not found")
    return {
        "vendor_id": row[0],
        "name": row[1],
        "currency": row[2],
        "status": row[3],
    }


@app.get("/po/{po_number}", response_model=PurchaseOrder)
def get_po(po_number: str) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT po_number, vendor_id, currency, status FROM erp.purchase_orders WHERE po_number = %s",
                (po_number,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="purchase order not found")
            cur.execute(
                "SELECT line_number, sku, description, quantity, unit_price FROM erp.po_line_items WHERE po_number = %s ORDER BY line_number",
                (po_number,),
            )
            lines = cur.fetchall()

    return {
        "po_number": row[0],
        "vendor_id": row[1],
        "currency": row[2],
        "status": row[3],
        "line_items": [
            {
                "line_number": line[0],
                "sku": line[1],
                "description": line[2],
                "quantity": float(line[3]),
                "unit_price": float(line[4]),
            }
            for line in lines
        ],
    }


@app.get("/sku/{sku_code}", response_model=SkuItem)
def get_sku(sku_code: str) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sku, description, uom, list_price, currency, active FROM erp.sku_master WHERE sku = %s",
                (sku_code,),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="sku not found")
    return {
        "sku": row[0],
        "description": row[1],
        "uom": row[2],
        "list_price": float(row[3]),
        "currency": row[4],
        "active": bool(row[5]),
    }
