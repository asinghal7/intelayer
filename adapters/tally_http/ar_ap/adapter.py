from __future__ import annotations
from datetime import date
from pathlib import Path
from jinja2 import Template
from adapters.tally_http.client import TallyClient


def _render(template_str: str, *, company: str) -> str:
    return Template(template_str).render(company=company)


def _render_with_dates(template_str: str, *, company: str, from_date: date, to_date: date) -> str:
    return Template(template_str).render(
        company=company,
        from_date=from_date.strftime("%d-%b-%Y"),
        to_date=to_date.strftime("%d-%b-%Y"),
    )


class TallyARAPAdapter:
    """
    Thin wrapper to fetch ledgers export with bill allocations exploded.
    Reuses the existing HTTP client pattern.
    """

    def __init__(self, url: str, company: str):
        self.client = TallyClient(url, company)
        self._tpl_ledgers_opening = (
            Path(__file__).resolve().parents[0]
            / "requests"
            / "ledgers_opening_bills.xml.j2"
        ).read_text(encoding="utf-8")
        self._tpl_outstanding_receivables = (
            Path(__file__).resolve().parents[0]
            / "requests"
            / "outstanding_receivables.xml.j2"
        ).read_text(encoding="utf-8")
        # Reuse daybook template for vouchers with bill allocations
        self._tpl_daybook = (
            Path(__file__).resolve().parents[1]
            / "requests"
            / "daybook.xml.j2"
        ).read_text(encoding="utf-8")

    def fetch_ledgers_with_opening_bills_xml(self) -> str:
        xml = _render(self._tpl_ledgers_opening, company=self.client.company)
        return self.client.post_xml(xml)

    def fetch_vouchers_with_bills_xml(self, from_date: date, to_date: date) -> str:
        """
        Fetch vouchers (daybook) with bill allocations for a date range.
        
        Reuses the daybook template which includes all voucher types with
        AllLedgerEntries.BillAllocations data.
        """
        xml = _render_with_dates(
            self._tpl_daybook,
            company=self.client.company,
            from_date=from_date,
            to_date=to_date,
        )
        return self.client.post_xml(xml)

    def fetch_outstanding_receivables_xml(self, as_of_date: date) -> str:
        """
        Fetch Outstanding Receivables report from Tally.
        
        This returns bill-wise outstanding amounts directly from Tally,
        which is more accurate than reconstructing from transactions.
        
        Args:
            as_of_date: Date as of which to fetch outstanding balances
        
        Returns:
            XML string containing outstanding receivables data
        """
        xml = _render_with_dates(
            self._tpl_outstanding_receivables,
            company=self.client.company,
            from_date=as_of_date,  # Use same date for from/to to get as-of snapshot
            to_date=as_of_date,
        )
        return self.client.post_xml(xml)




