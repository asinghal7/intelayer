**Apply the following additions/updates at repo root. Do not modify `.venv`, `.gitignore`, or unlisted files.**

```
Create or update files:
adapters/tally_http/validators.py
adapters/tally_http/client.py
adapters/tally_http/parser.py
adapters/tally_http/adapter.py
tests/fixtures/daybook_success.xml
tests/fixtures/daybook_empty.xml
tests/fixtures/status_error.xml
tests/test_parser_and_status.py
README.md (append a short “Testing” section)
```

**File: `adapters/tally_http/validators.py`**

```python
from __future__ import annotations
from lxml import etree

class TallyHTTPError(RuntimeError):
    pass

def ensure_status_ok(xml_text: str) -> None:
    """
    Raises TallyHTTPError if <STATUS> is missing or not '1'.
    Some “empty” responses still have STATUS=1; that's OK (caller can treat it as no data).
    """
    try:
        root = etree.fromstring(xml_text.encode("utf-8"))
    except Exception as e:
        raise TallyHTTPError(f"Invalid XML from Tally: {e}") from e

    status = root.findtext(".//STATUS")
    # STATUS is usually '1' for success. If absent, assume OK (older builds),
    # but if present and not '1' → error.
    if status is not None and status.strip() != "1":
        # Try to extract an error message if present
        msg = root.findtext(".//LINEERROR") or root.findtext(".//ERROR")
        raise TallyHTTPError(f"Tally returned STATUS={status} {('- ' + msg) if msg else ''}")
```

**Update: `adapters/tally_http/client.py`** (replace content with:)

```python
import requests
from tenacity import retry, wait_exponential, stop_after_attempt
from .validators import ensure_status_ok, TallyHTTPError

DEFAULT_HEADERS = {
    "Content-Type": "text/xml; charset=utf-8",
    "Accept": "text/xml",
    "User-Agent": "intelayer/0.1",
}

class TallyClient:
    def __init__(self, base_url: str, company: str):
        self.base_url = base_url.rstrip("/")
        self.company = company
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30),
           stop=stop_after_attempt(5))
    def post_xml(self, xml: str, timeout: int = 60) -> str:
        r = self.session.post(self.base_url, data=xml.encode("utf-8"), timeout=timeout)
        r.raise_for_status()
        text = r.text
        ensure_status_ok(text)  # raises if STATUS != 1
        return text
```

**Update: `adapters/tally_http/parser.py`** (replace content with:)

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

def parse_daybook(xml_text: str) -> list[dict]:
    """
    Parse DayBook XML: return a list of voucher dicts (header-level).
    Extend later with nested line parsing via custom Collection.
    """
    root = etree.fromstring(xml_text.encode("utf-8"))
    out: list[dict] = []
    for v in root.findall(".//VOUCHER"):
        out.append({
            "vchtype": v.get("VCHTYPE") or "",
            "vchnumber": v.get("VCHNUMBER") or "",
            "date": parse_tally_date(v.findtext("DATE")),
            "party": (v.findtext("PARTYLEDGERNAME") or "").strip(),
            "amount": float((v.findtext("AMOUNT") or "0").strip() or 0),
            "guid": v.get("GUID") or "",
        })
    return out
```

**Update: `adapters/tally_http/adapter.py`** (ensure these helpers exist / replace if needed)

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
```

**File: `tests/fixtures/daybook_success.xml`**

```xml
<ENVELOPE>
  <HEADER><VERSION>1</VERSION><STATUS>1</STATUS></HEADER>
  <BODY><DATA><TALLYMESSAGE>
    <VOUCHER VCHTYPE="Sales" VCHNUMBER="S-101" GUID="abcd-1234">
      <DATE>20251011</DATE>
      <PARTYLEDGERNAME>Acme Distributors</PARTYLEDGERNAME>
      <AMOUNT>1234.50</AMOUNT>
    </VOUCHER>
  </TALLYMESSAGE></DATA></BODY>
</ENVELOPE>
```

**File: `tests/fixtures/daybook_empty.xml`**

```xml
<ENVELOPE>
  <HEADER><VERSION>1</VERSION><STATUS>1</STATUS></HEADER>
  <BODY><DATA/></BODY>
</ENVELOPE>
```

**File: `tests/fixtures/status_error.xml`**

```xml
<ENVELOPE>
  <HEADER><VERSION>1</VERSION><STATUS>0</STATUS></HEADER>
  <BODY><LINEERROR>Company not open</LINEERROR></BODY>
</ENVELOPE>
```

**File: `tests/test_parser_and_status.py`**

```python
from pathlib import Path
import pytest
from adapters.tally_http.parser import parse_daybook
from adapters.tally_http.validators import ensure_status_ok, TallyHTTPError

FIX = Path(__file__).parent / "fixtures"

def read(p): return (FIX / p).read_text(encoding="utf-8")

def test_status_ok_and_parse_daybook():
    xml = read("daybook_success.xml")
    ensure_status_ok(xml)  # no raise
    rows = parse_daybook(xml)
    assert len(rows) == 1
    r = rows[0]
    assert r["vchtype"] == "Sales"
    assert r["vchnumber"] == "S-101"
    assert r["party"] == "Acme Distributors"
    assert r["amount"] == 1234.50

def test_empty_ok():
    xml = read("daybook_empty.xml")
    ensure_status_ok(xml)  # status 1 but no DATA
    assert parse_daybook(xml) == []

def test_status_error_raises():
    xml = read("status_error.xml")
    with pytest.raises(TallyHTTPError):
        ensure_status_ok(xml)
```

**Update (append) to: `README.md`**

```md
## Testing
- Install test tools (inside your existing venv):
  `pip install -e . pytest`
- Run tests:
  `pytest -q`

These tests validate: (1) STATUS handling, (2) DayBook parsing, (3) empty responses.
```