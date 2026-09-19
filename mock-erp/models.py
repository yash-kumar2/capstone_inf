from __future__ import annotations

from pydantic import BaseModel, Field


class Vendor(BaseModel):
    vendor_id: str
    name: str
    currency: str
    status: str


class LineItem(BaseModel):
    line_number: int
    sku: str
    description: str
    quantity: float
    unit_price: float


class PurchaseOrder(BaseModel):
    po_number: str
    vendor_id: str
    currency: str
    status: str
    line_items: list[LineItem] = Field(default_factory=list)


class SkuItem(BaseModel):
    sku: str
    description: str
    uom: str
    list_price: float
    currency: str
    active: bool
