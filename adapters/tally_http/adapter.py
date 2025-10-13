from __future__ import annotations
from datetime import date
from jinja2 import Template
from adapters.adapter_types import Invoice
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

    def fetch_invoices(self, since: date, to: date):
        xml = _render(self.daybook_template, from_date=since, to_date=to, company=self.client.company)
        for d in parse_daybook(self.client.post_xml(xml)):
            # Skip filtering if include_types is empty (include all)
            if self.include_types and d["vchtype"] not in self.include_types:
                continue
            
            # Extract subtotal (pre-tax) and total (post-tax)
            subtotal = float(d.get("subtotal") or 0.0)
            total = float(d.get("total") or 0.0)
            
            # Calculate tax as difference between total and subtotal
            tax = total - subtotal
            
            yield Invoice(
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
