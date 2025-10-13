from typing import Protocol, Iterable
from pydantic import BaseModel
from datetime import date

class Customer(BaseModel):
    customer_id: str
    name: str
    gstin: str | None = None
    city: str | None = None
    pincode: str | None = None

class Item(BaseModel):
    item_id: str
    sku: str | None = None
    name: str
    brand: str | None = None
    hsn: str | None = None
    uom: str | None = None

class InvoiceLine(BaseModel):
    item_id: str
    qty: float
    rate: float
    line_total: float
    tax: float | None = None

class Invoice(BaseModel):
    invoice_id: str
    voucher_key: str
    vchtype: str                 # <-- NEW: store voucher type
    date: date
    customer_id: str
    sp_id: str | None = None
    subtotal: float
    tax: float
    total: float
    roundoff: float | None = 0.0
    lines: list[InvoiceLine]

class Receipt(BaseModel):
    receipt_key: str
    date: date
    customer_id: str
    amount: float

class ERPAdapter(Protocol):
    def fetch_customers(self, since: date | None) -> Iterable[Customer]: ...
    def fetch_items(self, since: date | None) -> Iterable[Item]: ...
    def fetch_invoices(self, since: date, to: date) -> Iterable[Invoice]: ...
    def fetch_receipts(self, since: date, to: date) -> Iterable[Receipt]: ...

