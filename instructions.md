I want to fix the **0-amount problem** where my metabase db is showing amount as 0 for all fact invoice rows through the following plan which - (by computing the signed amount from the party ledger line), preserves **polarity**, and adds a small schema + ETL tweak so your dashboards can filter by **voucher type**. Don’t touch `.venv` or other unlisted files. Ensure previous fixes don't get disrupted due to this fix, hence implement the below carefully, making intelligent choices.

---

Create/overwrite the following files:

```
adapters/adapter_types.py
adapters/tally_http/parser.py
adapters/tally_http/adapter.py
agent/run.py
warehouse/migrations/0002_add_vchtype.sql
tests/fixtures/daybook_header_empty_with_lines.xml
tests/test_amount_signed_and_party_line.py
README.md (append a short note)
```

---

**File: `adapters/adapter_types.py`** (add `vchtype` to `Invoice`)

```python
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
```

---

**File: `adapters/tally_http/parser.py`** (robust signed amount from PARTY line; no `abs()` baked in)

```python
from __future__ import annotations
from lxml import etree
from datetime import datetime, date

def parse_tally_date(s: str | None) -> date:
    if not s:
        return date.today()
    s = s.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return date.today()

def _to_float(x: str | None) -> float:
    if not x:
        return 0.0
    x = x.replace(",", "").strip()
    neg = x.startswith("(") and x.endswith(")")
    if neg:
        x = x[1:-1]
    try:
        val = float(x or 0.0)
    except ValueError:
        val = 0.0
    return -val if neg else val

def _party_line_amount_signed(voucher: etree._Element, party_name: str) -> float | None:
    party = (party_name or "").strip().lower()
    for le in voucher.findall(".//ALLLEDGERENTRIES.LIST"):
        lname = (le.findtext("LEDGERNAME") or "").strip().lower()
        if lname == party:
            return _to_float(le.findtext("AMOUNT"))  # keep sign
    return None

def _fallback_amount_signed(voucher: etree._Element) -> float:
    # choose the line with largest magnitude; keep its original sign
    best_val = 0.0
    best_abs = 0.0
    for le in voucher.findall(".//ALLLEDGERENTRIES.LIST"):
        v = _to_float(le.findtext("AMOUNT"))
        if abs(v) > best_abs:
            best_abs = abs(v)
            best_val = v
    return best_val

def parse_daybook(xml_text: str) -> list[dict]:
    """
    Return vouchers with signed 'amount' derived from party ledger line when possible.
    Fields: vchtype, vchnumber, date, party, amount (signed), guid
    """
    root = etree.fromstring(xml_text.encode("utf-8"))
    out: list[dict] = []
    for v in root.findall(".//VOUCHER"):
        vchtype = v.get("VCHTYPE") or ""
        vchnumber = v.get("VCHNUMBER") or ""
        guid = v.get("GUID") or ""
        d = parse_tally_date(v.findtext("DATE"))
        party = (v.findtext("PARTYLEDGERNAME") or "").strip()

        amt = _party_line_amount_signed(v, party)
        if amt is None:
            amt = _fallback_amount_signed(v)
        if amt == 0.0:
            # last resort: header-level AMOUNT if present (often blank)
            amt = _to_float(v.findtext("AMOUNT"))

        out.append({
            "vchtype": vchtype,
            "vchnumber": vchnumber,
            "date": d,
            "party": party,
            "amount": amt,  # signed!
            "guid": guid,
        })
    return out
```

---

**File: `adapters/tally_http/adapter.py`** (feed `vchtype` into Invoice; default include Sales + CN/SR)

```python
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
    return d.get("guid") or f"{d.get('vchtype','')}/{d.get('vchnumber','')}/{d.get('date','')}/{d.get('party','')}"

class TallyHTTPAdapter:
    def __init__(self, url: str, company: str, daybook_template: str, include_types: set[str] | None = None):
        self.client = TallyClient(url, company)
        self.daybook_template = daybook_template
        # Include common sales document types; adjust later if needed
        self.include_types = include_types or {"Sales", "Credit Note", "Sales Return"}

    def fetch_invoices(self, since: date, to: date):
        xml = _render(self.daybook_template, from_date=since, to_date=to, company=self.client.company)
        for d in parse_daybook(self.client.post_xml(xml)):
            if d["vchtype"] not in self.include_types:
                continue
            amt = float(d.get("amount") or 0.0)  # signed
            yield Invoice(
                invoice_id=_voucher_key(d),
                voucher_key=_voucher_key(d),
                vchtype=d["vchtype"],
                date=d["date"],
                customer_id=d.get("party","") or "UNKNOWN",
                sp_id=None,
                subtotal=amt,
                tax=0.0,
                total=amt,
                roundoff=0.0,
                lines=[],
            )
```

---

**File: `agent/run.py`** (upsert `vchtype` too)

```python
from datetime import date, timedelta
import psycopg
from loguru import logger
from pathlib import Path
from adapters.tally_http.adapter import TallyHTTPAdapter
from agent.settings import TALLY_URL, TALLY_COMPANY, DB_URL

DAYBOOK_TEMPLATE = (Path(__file__).resolve().parents[1] / "adapters" / "tally_http" / "requests" / "daybook.xml.j2").read_text(encoding="utf-8")

def get_checkpoint(conn, stream: str) -> date:
    with conn.cursor() as cur:
        cur.execute("select last_date from etl_checkpoints where stream_name=%s", (stream,))
        row = cur.fetchone()
        fy_start = date(date.today().year if date.today().month>=4 else date.today().year-1, 4, 1)
        return row[0] if row and row[0] else fy_start

def upsert_invoice(conn, inv):
    with conn.cursor() as cur:
        cur.execute("""
          insert into fact_invoice (invoice_id, voucher_key, vchtype, date, customer_id, sp_id, subtotal, tax, total, roundoff)
          values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
          on conflict (invoice_id) do update set
            vchtype=excluded.vchtype,
            date=excluded.date,
            customer_id=excluded.customer_id,
            subtotal=excluded.subtotal,
            tax=excluded.tax,
            total=excluded.total,
            roundoff=excluded.roundoff
        """, (
            inv.invoice_id, inv.voucher_key, inv.vchtype, inv.date, inv.customer_id, inv.sp_id,
            inv.subtotal, inv.tax, inv.total, inv.roundoff
        ))

def log_run(conn, rows: int, status: str, err: str | None = None):
    with conn.cursor() as cur:
        cur.execute("insert into etl_logs(stream_name, rows, status, error) values(%s,%s,%s,%s)",
                    ("invoices", rows, status, err))

def main():
    adapter = TallyHTTPAdapter(TALLY_URL, TALLY_COMPANY, DAYBOOK_TEMPLATE)
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        try:
            last = get_checkpoint(conn, "invoices")
            start = last - timedelta(days=1)  # overlap for late edits
            end = date.today()
            count = 0
            for inv in adapter.fetch_invoices(start, end):
                upsert_invoice(conn, inv); count += 1
            with conn.cursor() as cur:
                cur.execute("""
                  insert into etl_checkpoints(stream_name,last_date) values('invoices', %s)
                  on conflict(stream_name) do update set last_date=excluded.last_date, updated_at=now()
                """, (end,))
            log_run(conn, count, "ok")
            logger.info(f"Invoices upserted: {count}")
        except Exception as e:
            log_run(conn, 0, "error", str(e))
            raise

if __name__ == "__main__":
    main()
```

---

**File: `warehouse/migrations/0002_add_vchtype.sql`** (schema tweak for filtering/analytics)

```sql
alter table fact_invoice
  add column if not exists vchtype text;

create index if not exists idx_fact_invoice_vchtype on fact_invoice(vchtype);
```

---

**File: `tests/fixtures/daybook_header_empty_with_lines.xml`**

```xml
<ENVELOPE>
  <HEADER><VERSION>1</VERSION><STATUS>1</STATUS></HEADER>
  <BODY><DATA><TALLYMESSAGE>
    <VOUCHER VCHTYPE="Sales" VCHNUMBER="S-200" GUID="guid-200">
      <DATE>20251012</DATE>
      <PARTYLEDGERNAME>Acme Distributors</PARTYLEDGERNAME>
      <!-- No header-level AMOUNT -->
      <ALLLEDGERENTRIES.LIST>
        <LEDGERNAME>Sales A/c</LEDGERNAME>
        <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
        <AMOUNT>-1234.50</AMOUNT>
      </ALLLEDGERENTRIES.LIST>
      <ALLLEDGERENTRIES.LIST>
        <LEDGERNAME>Acme Distributors</LEDGERNAME>
        <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
        <AMOUNT>1234.50</AMOUNT>
      </ALLLEDGERENTRIES.LIST>
    </VOUCHER>
  </TALLYMESSAGE></DATA></BODY>
</ENVELOPE>
```

---

**File: `tests/test_amount_signed_and_party_line.py`**

```python
from pathlib import Path
from adapters.tally_http.parser import parse_daybook

def test_amount_from_party_line_signed():
    xml = (Path(__file__).parent / "fixtures" / "daybook_header_empty_with_lines.xml").read_text(encoding="utf-8")
    rows = parse_daybook(xml)
    assert len(rows) == 1
    r = rows[0]
    assert r["vchtype"] == "Sales"
    assert r["vchnumber"] == "S-200"
    assert r["party"] == "Acme Distributors"
    # Should pick party ledger line with sign preserved (Sales -> customer debit -> +)
    assert r["amount"] == 1234.50
```

---

**Update (append) to: `README.md`**

```md
### After fixing 0-amounts
- Apply migration:
  - If using Docker:  
    `docker compose -f ops/docker-compose.yml cp warehouse/migrations/0002_add_vchtype.sql db:/tmp/0002_add_vchtype.sql`  
    `docker compose -f ops/docker-compose.yml exec db psql -U inteluser -d intelayer -f /tmp/0002_add_vchtype.sql`
- Run tests: `pytest -q`
- Re-run ETL for today: `python agent/run.py`
- In SQL or Metabase, you can now filter by `vchtype` and totals are **signed** (Sales +, Credit Note/Return -).
```

**END OF PROMPT**
