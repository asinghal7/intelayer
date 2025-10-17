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

def _party_line_amount_signed(voucher: etree._Element, party_name: str, vchtype: str = None) -> float | None:
    """
    Extract party ledger amount with voucher-type aware tag selection.
    - For Invoice vouchers: Check LEDGERENTRIES.LIST (single R)
    - For other vouchers: Check ALLLEDGERENTRIES.LIST (double L)
    """
    party = (party_name or "").strip().lower()
    
    # For Invoice vouchers, check LEDGERENTRIES.LIST (single R)
    if vchtype == "Invoice":
        for le in voucher.findall(".//LEDGERENTRIES.LIST"):
            lname = (le.findtext("LEDGERNAME") or "").strip().lower()
            if lname == party or party[:15] in lname[:15]:
                return _to_float(le.findtext("AMOUNT"))  # keep sign
    
    # For all other voucher types, check ALLLEDGERENTRIES.LIST (double L)
    for le in voucher.findall(".//ALLLEDGERENTRIES.LIST"):
        lname = (le.findtext("LEDGERNAME") or "").strip().lower()
        if lname == party or party[:15] in lname[:15]:
            return _to_float(le.findtext("AMOUNT"))  # keep sign
    
    return None

def _fallback_amount_signed(voucher: etree._Element, vchtype: str = None) -> float:
    """
    Choose the line with largest magnitude; keep its original sign.
    - For Invoice vouchers: Check LEDGERENTRIES.LIST (single R)
    - For other vouchers: Check ALLLEDGERENTRIES.LIST (double L)
    """
    best_val = 0.0
    best_abs = 0.0
    
    # For Invoice vouchers, check LEDGERENTRIES.LIST (single R)
    if vchtype == "Invoice":
        for le in voucher.findall(".//LEDGERENTRIES.LIST"):
            v = _to_float(le.findtext("AMOUNT"))
            if abs(v) > best_abs:
                best_abs = abs(v)
                best_val = v
    
    # For all other voucher types, check ALLLEDGERENTRIES.LIST (double L)
    for le in voucher.findall(".//ALLLEDGERENTRIES.LIST"):
        v = _to_float(le.findtext("AMOUNT"))
        if abs(v) > best_abs:
            best_abs = abs(v)
            best_val = v
    
    return best_val

def _bill_allocation_amount(voucher: etree._Element) -> float | None:
    """
    Extract amount from BILLALLOCATIONS.LIST (post-tax total for invoices).
    This is the most accurate for Invoice vouchers as it includes tax.
    Returns None if not found.
    """
    for bill_alloc in voucher.findall(".//BILLALLOCATIONS.LIST"):
        amt_text = bill_alloc.findtext("AMOUNT")
        if amt_text:
            # Return absolute value (bill allocations are typically negative)
            return abs(_to_float(amt_text))
    return None

def _inventory_total_amount(voucher: etree._Element) -> float:
    """
    Calculate total amount from inventory entries (pre-tax).
    Used as fallback for Invoice/Sales vouchers where bill allocation is not available.
    Note: This gives pre-tax total, so should be used as last resort.
    """
    total = 0.0
    for inv_entry in voucher.findall(".//ALLINVENTORYENTRIES.LIST"):
        amt = _to_float(inv_entry.findtext("AMOUNT"))
        total += amt
    return total

def _parse_inventory_entries(voucher: etree._Element) -> list[dict]:
    """
    Parse individual inventory entries from a voucher.
    Returns list of dicts with: stock_item_name, billed_qty, rate, amount, discount
    """
    entries = []
    for inv_entry in voucher.findall(".//ALLINVENTORYENTRIES.LIST"):
        stock_item_name = (inv_entry.findtext("STOCKITEMNAME") or "").strip()
        billed_qty = (inv_entry.findtext("BILLEDQTY") or "").strip()
        rate = (inv_entry.findtext("RATE") or "").strip()
        amount = _to_float(inv_entry.findtext("AMOUNT"))
        discount = _to_float(inv_entry.findtext("DISCOUNT"))
        
        if stock_item_name:  # Only include entries with item names
            entries.append({
                "stock_item_name": stock_item_name,
                "billed_qty": billed_qty,
                "rate": rate,
                "amount": amount,
                "discount": discount
            })
    return entries

def parse_daybook(xml_text: str) -> list[dict]:
    """
    Return vouchers with amounts separated into subtotal (pre-tax) and total (post-tax).
    Fields: vchtype, vchnumber, date, party, amount (for backward compat), subtotal, total, guid, 
            party_gstin, party_pincode, party_city, inventory_entries
    """
    # Sanitize XML to remove invalid characters
    sanitized = sanitize_xml(xml_text)
    root = etree.fromstring(sanitized.encode("utf-8"))
    out: list[dict] = []
    for v in root.findall(".//VOUCHER"):
        vchtype = v.get("VCHTYPE") or ""
        vchnumber = v.get("VCHNUMBER") or ""
        # Use GUID if available, otherwise use REMOTEID (Tally's unique voucher identifier)
        guid = v.get("GUID") or v.get("REMOTEID") or ""
        d = parse_tally_date(v.findtext("DATE"))
        party = (v.findtext("PARTYLEDGERNAME") or "").strip()
        
        # Extract party/customer master details
        # Try multiple possible XML paths where Tally might store this info
        party_gstin = (v.findtext("PARTYGSTIN") or 
                      v.findtext(".//PARTYGSTIN") or 
                      v.findtext(".//BASICBUYERPARTYGSTIN") or "").strip()
        
        party_pincode = (v.findtext("PARTYPINCODE") or 
                        v.findtext(".//PARTYPINCODE") or 
                        v.findtext(".//BASICBUYERPINCODE") or "").strip()
        
        party_city = (v.findtext("PARTYCITY") or 
                     v.findtext(".//PARTYCITY") or 
                     v.findtext(".//BASICBUYERSTATE") or "").strip()

        # For invoices, try to get both pre-tax (subtotal) and post-tax (total)
        subtotal = 0.0
        total = 0.0
        
        # Get inventory total (pre-tax for invoices)
        amt_from_inventory = _inventory_total_amount(v)
        
        # Try to get post-tax amount from ledger entries (voucher-type aware)
        amt_from_ledger = _party_line_amount_signed(v, party, vchtype)
        if amt_from_ledger is None:
            amt_from_ledger = _fallback_amount_signed(v, vchtype)
        
        # Also check bill allocation (works for most invoices)
        amt_from_bill = _bill_allocation_amount(v)
        
        # Determine subtotal and total based on what's available
        if amt_from_inventory and (amt_from_ledger or amt_from_bill):
            # Invoice with both pre-tax and post-tax amounts
            subtotal = amt_from_inventory  # Pre-tax from inventory
            # Prefer ledger amount (more universal), fallback to bill allocation
            total = abs(amt_from_ledger) if amt_from_ledger else amt_from_bill
        elif amt_from_ledger:
            # Has ledger amount but no inventory - use ledger for both
            total = abs(amt_from_ledger)
            subtotal = total  # No separate tax information
        elif amt_from_bill:
            # Has bill allocation but no inventory
            total = amt_from_bill
            subtotal = total  # No separate tax information
        elif amt_from_inventory:
            # Has inventory only (no post-tax found)
            subtotal = amt_from_inventory
            total = amt_from_inventory
        else:
            # Last resort: header-level AMOUNT
            amt = _to_float(v.findtext("AMOUNT"))
            subtotal = amt
            total = amt

        # Parse inventory entries for line items
        inventory_entries = _parse_inventory_entries(v)

        out.append({
            "vchtype": vchtype,
            "vchnumber": vchnumber,
            "date": d,
            "party": party,
            "amount": total,  # backward compatibility - use total
            "subtotal": subtotal,  # pre-tax amount
            "total": total,  # post-tax amount
            "guid": guid,
            "party_gstin": party_gstin if party_gstin else None,
            "party_pincode": party_pincode if party_pincode else None,
            "party_city": party_city if party_city else None,
            "inventory_entries": inventory_entries,
        })
    return out
