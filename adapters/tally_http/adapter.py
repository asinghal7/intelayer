from __future__ import annotations
from datetime import date
from jinja2 import Template
from adapters.adapter_types import Invoice, Receipt
from .client import TallyClient
from .parser import parse_daybook
import hashlib

def _render(template_str: str, *, from_date: date, to_date: date, company: str) -> str:
    return Template(template_str).render(
        from_date=from_date.strftime("%d-%b-%Y"),
        to_date=to_date.strftime("%d-%b-%Y"),
        company=company,
    )

def _voucher_key(d: dict) -> str:
    """Generate a unique key for a voucher.
    
    Priority:
    1. If GUID exists, use it (most reliable)
    2. If vchnumber exists, use vchtype/vchnumber/date/party
    3. Otherwise, generate a hash of all fields to ensure uniqueness
    """
    guid = d.get("guid", "").strip()
    if guid:
        return guid
    
    vchnumber = d.get("vchnumber", "").strip()
    if vchnumber:
        return f"{d.get('vchtype','')}/{vchnumber}/{d.get('date','')}/{d.get('party','')}"
    
    # No GUID and no vchnumber - create a unique hash
    # Include all available fields to ensure uniqueness
    key_data = (
        f"{d.get('vchtype','')}"
        f"|{d.get('date','')}"
        f"|{d.get('party','')}"
        f"|{d.get('amount', 0)}"
    )
    # Use first 16 chars of hash for readability
    hash_suffix = hashlib.sha256(key_data.encode()).hexdigest()[:16]
    return f"{d.get('vchtype','')}/{d.get('date','')}/{d.get('party','')}#{hash_suffix}"

class TallyHTTPAdapter:
    def __init__(self, url: str, company: str, daybook_template: str, include_types: set[str] | None = None):
        self.client = TallyClient(url, company)
        self.daybook_template = daybook_template
        # If None, include ALL voucher types. If set provided, filter by those types.
        # Default: include common sales document types
        if include_types is None:
            self.include_types = {"Sales", "Credit Note", "Sales Return"}
        else:
            self.include_types = include_types
        # Cache for storing last fetched vouchers (to reuse for receipts)
        self._last_vouchers_cache = []

    def fetch_invoices(self, since: date, to: date):
        xml = _render(self.daybook_template, from_date=since, to_date=to, company=self.client.company)
        # Parse and cache vouchers for potential reuse (e.g., for receipts)
        self._last_vouchers_cache = list(parse_daybook(self.client.post_xml(xml)))
        
        for d in self._last_vouchers_cache:
            # Skip filtering if include_types is empty (include all)
            if self.include_types and d["vchtype"] not in self.include_types:
                continue
            
            # Extract subtotal (pre-tax) and total (post-tax)
            subtotal = float(d.get("subtotal") or 0.0)
            total = float(d.get("total") or 0.0)
            
            # Calculate tax as difference between total and subtotal
            tax = total - subtotal
            
            # Create invoice with embedded customer details
            # Store customer details in a special attribute for upsert
            invoice = Invoice(
                invoice_id=_voucher_key(d),
                voucher_key=_voucher_key(d),
                vchtype=d["vchtype"],
                date=d["date"],
                customer_id=d.get("party","") or "UNKNOWN",
                sp_id=None,
                subtotal=subtotal,
                tax=tax,
                total=total,
                roundoff=0.0,
                lines=[],
            )
            
            # Attach customer master data as extra attributes (not part of Invoice model)
            # This will be used by upsert_customer function
            invoice.__dict__["_customer_gstin"] = d.get("party_gstin")
            invoice.__dict__["_customer_pincode"] = d.get("party_pincode")
            invoice.__dict__["_customer_city"] = d.get("party_city")
            
            yield invoice
    
    def get_receipts_from_last_fetch(self):
        """Extract Receipt vouchers from the cached data (last fetch_invoices call).
        
        This reuses the XML response that was already fetched by fetch_invoices(),
        avoiding an additional Tally request.
        
        Yields:
            Receipt: Receipt objects for vouchers with vchtype='Receipt'
        """
        for d in self._last_vouchers_cache:
            # Only process Receipt voucher types
            if d["vchtype"] != "Receipt":
                continue
            
            # For receipts, use the total amount
            amount = float(d.get("total") or 0.0)
            
            # Create receipt with customer details
            receipt = Receipt(
                receipt_key=_voucher_key(d),
                date=d["date"],
                customer_id=d.get("party","") or "UNKNOWN",
                amount=amount,
            )
            
            # Attach customer master data (same pattern as invoices)
            receipt.__dict__["_customer_gstin"] = d.get("party_gstin")
            receipt.__dict__["_customer_pincode"] = d.get("party_pincode")
            receipt.__dict__["_customer_city"] = d.get("party_city")
            
            yield receipt
