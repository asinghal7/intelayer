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
