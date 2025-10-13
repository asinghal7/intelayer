from __future__ import annotations
from datetime import date
from jinja2 import Template
from adapters.adapter_types import Invoice
from .client import TallyClient
from .parser import parse_daybook

def _render(template_str: str, *, from_date: date, to_date: date, company: str) -> str:
    return Template(template_str).render(
        from_date=from_date.strftime("%d-%b-%Y"),
        to_date=to_date.strftime("%d-%b-%Y"),
        company=company,
    )

def _voucher_key(d: dict) -> str:
    # Prefer GUID if present, else stable tuple
    return d.get("guid") or f"{d.get('vchtype','')}/{d.get('vchnumber','')}/{d.get('date','')}/{d.get('party','')}"

class TallyHTTPAdapter:
    def __init__(self, url: str, company: str, daybook_template: str):
        self.client = TallyClient(url, company)
        self.daybook_template = daybook_template

    def fetch_invoices(self, since: date, to: date):
        xml = _render(self.daybook_template, from_date=since, to_date=to, company=self.client.company)
        resp = self.client.post_xml(xml)
        for d in parse_daybook(resp):
            amt = float(d.get("amount") or 0.0)
            yield Invoice(
                invoice_id=_voucher_key(d),   # GUID if present
                voucher_key=_voucher_key(d),
                date=d["date"],
                customer_id=d.get("party","") or "UNKNOWN",
                sp_id=None,
                subtotal=amt,
                tax=0.0,
                total=amt,
                roundoff=0.0,
                lines=[],
            )
