from __future__ import annotations
from lxml import etree
from datetime import datetime, date
from .validators import sanitize_xml

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
    # Sanitize XML to remove invalid characters
    sanitized = sanitize_xml(xml_text)
    root = etree.fromstring(sanitized.encode("utf-8"))
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
