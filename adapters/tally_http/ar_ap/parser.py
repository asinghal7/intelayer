"""
Parser for AR/AP opening bill allocations from Tally Ledgers export.

This reads LEDGER.BILLALLOCATIONS.LIST from the standard "List of Accounts → Ledgers"
export with EXPLODEFLAG=Yes.

Output rows:
- ledger: ledger name (key)
- name: bill/ref name
- bill_date: date
- opening_balance: numeric amount
- bill_credit_period: integer days (if available)
- is_advance: boolean
"""
from __future__ import annotations
from datetime import datetime, date
from lxml import etree
from adapters.tally_http.validators import sanitize_xml


def _text(element: etree._Element | None, tag: str) -> str | None:
    if element is None:
        return None
    val = element.findtext(tag)
    if val is None:
        return None
    val = val.strip()
    return val if val else None


def _bool(element: etree._Element | None, tag: str) -> bool:
    val = _text(element, tag)
    if val is None:
        return False
    return val.lower() in ("yes", "y", "true", "1")


def _num(element: etree._Element | None, tag: str) -> float:
    val = _text(element, tag)
    if not val:
        return 0.0
    # Replace accounting style (-) with - and strip commas
    cleaned = val.replace("(-)", "-").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_opening_bill_allocations(xml_text: str) -> list[dict]:
    sanitized = sanitize_xml(xml_text)
    root = etree.fromstring(sanitized.encode("utf-8"))

    out: list[dict] = []

    # Iterate Ledgers and their BILLALLOCATIONS children
    for ledger in root.findall(".//LEDGER"):
        ledger_name = ledger.get("NAME")
        if not ledger_name:
            continue
        for bill in ledger.findall(".//BILLALLOCATIONS.LIST"):
            # Only consider records that look like opening allocations (have OpeningBalance or BillDate/Name)
            name = _text(bill, "NAME")
            bill_date = _text(bill, "BILLDATE")
            opening_balance = _num(bill, "OPENINGBALANCE")
            bill_credit_period = _text(bill, "BILLCREDITPERIOD")
            is_advance = _bool(bill, "ISADVANCE")

            # Normalize credit period to int where possible
            credit_days = None
            if bill_credit_period:
                try:
                    credit_days = int(str(bill_credit_period).strip())
                except Exception:
                    credit_days = None

            out.append({
                "ledger": ledger_name.strip(),
                "name": name or "",
                "bill_date": bill_date,
                "opening_balance": round(opening_balance, 2),
                "bill_credit_period": credit_days,
                "is_advance": bool(is_advance),
            })

    return out


def parse_tally_date(s: str | None) -> date:
    """Parse Tally date format to Python date."""
    if not s:
        return date.today()
    s = s.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return date.today()


def parse_outstanding_receivables(xml_text: str) -> list[dict]:
    """
    Parse Outstanding Receivables report from Tally.
    
    This extracts bill-wise outstanding amounts directly from Tally's
    Outstanding Receivables report, which is more accurate than reconstructing
    from transactions.
    
    Returns list of dicts with keys:
    - ledger: Ledger name
    - bill_name: Bill reference name
    - bill_date: Bill date
    - original_amount: Original bill amount
    - pending_amount: Outstanding amount
    - due_date: Due date (if available)
    - billtype: Bill type
    - is_advance: Whether it's an advance
    """
    sanitized = sanitize_xml(xml_text)
    root = etree.fromstring(sanitized.encode("utf-8"))
    
    out: list[dict] = []
    
    # Iterate through ledgers
    for ledger in root.findall(".//LEDGER"):
        ledger_name = ledger.get("NAME")
        if not ledger_name:
            continue
        
        # Find bill allocations within this ledger
        for bill_alloc in ledger.findall(".//BILLALLOCATIONS.LIST"):
            bill_name = _text(bill_alloc, "NAME")
            if not bill_name:
                continue
            
            # Extract bill details
            bill_date_str = _text(bill_alloc, "BILLDATE")
            bill_date = parse_tally_date(bill_date_str) if bill_date_str else None
            
            # Amounts
            opening_balance = _num(bill_alloc, "OPENINGBALANCE")
            amount = _num(bill_alloc, "AMOUNT")
            
            # For outstanding receivables:
            # - OPENINGBALANCE is the original amount (negative for receivables)
            # - AMOUNT is the current outstanding (negative for receivables)
            # Both are typically negative for debtors, convert to positive
            original_amount = abs(opening_balance) if opening_balance else abs(amount)
            pending_amount = abs(amount)
            
            # Other fields
            bill_credit_period = _text(bill_alloc, "BILLCREDITPERIOD")
            credit_days = None
            if bill_credit_period:
                try:
                    credit_days = int(str(bill_credit_period).strip())
                except Exception:
                    credit_days = None
            
            due_date = None
            if bill_date and credit_days:
                from datetime import timedelta
                due_date = bill_date + timedelta(days=credit_days)
            
            billtype = _text(bill_alloc, "BILLTYPE") or "Outstanding"
            is_advance = _bool(bill_alloc, "ISADVANCE")
            
            out.append({
                "ledger": ledger_name.strip(),
                "bill_name": bill_name.strip(),
                "bill_date": bill_date,
                "original_amount": round(original_amount, 2),
                "pending_amount": round(pending_amount, 2),
                "due_date": due_date,
                "billtype": billtype,
                "is_advance": is_advance,
            })
    
    return out


def parse_trn_bill_allocations(xml_text: str) -> list[dict]:
    """
    Parse bill allocations from voucher exports (daybook).
    
    Extracts Voucher.AllLedgerEntries.BillAllocations from daybook XML.
    Handles both "New Ref" (positive, creates new bill) and "Agst Ref" (negative, payment/adjustment).
    
    Returns list of dicts with keys:
    - voucher_guid: Voucher GUID
    - voucher_date: Voucher date
    - ledger: Ledger name
    - bill_name: Bill reference name
    - amount: Bill amount (numeric, preserves sign)
    - billtype: Bill type ("New Ref" or "Agst Ref")
    - bill_credit_period: Credit period in days (if available)
    """
    sanitized = sanitize_xml(xml_text)
    root = etree.fromstring(sanitized.encode("utf-8"))
    
    out: list[dict] = []
    
    # Iterate through all vouchers
    for voucher in root.findall(".//VOUCHER"):
        voucher_guid = _text(voucher, "GUID")
        voucher_date_str = _text(voucher, "DATE")
        voucher_date = parse_tally_date(voucher_date_str)
        voucher_type = voucher.get("VCHTYPE") or _text(voucher, "VOUCHERTYPENAME") or ""
        voucher_number = voucher.get("VCHNUMBER") or _text(voucher, "VOUCHERNUMBER") or ""
        reference_number = _text(voucher, "REFERENCE")
        reference_date_str = _text(voucher, "REFERENCEDATE")
        reference_date = parse_tally_date(reference_date_str) if reference_date_str else None
        narration = _text(voucher, "NARRATION")
        party_name = _text(voucher, "PARTYLEDGERNAME")
        place_of_supply = _text(voucher, "PLACEOFSUPPLY")
        is_invoice = _bool(voucher, "ISINVOICE")
        is_accounting_voucher = _bool(voucher, "ISACCOUNTINGVOUCHER")
        is_inventory_voucher = _bool(voucher, "ISINVENTORYVOUCHER")
        is_order_voucher = _bool(voucher, "ISORDERVOUCHER")
        alter_id_text = _text(voucher, "ALTERID")
        try:
            alter_id = int(alter_id_text) if alter_id_text else None
        except ValueError:
            alter_id = None
        
        if not voucher_guid:
            continue
        
        # Find all ledger entries with bill allocations
        for ledger_entry in voucher.findall(".//ALLLEDGERENTRIES.LIST"):
            ledger_name = _text(ledger_entry, "LEDGERNAME")
            if not ledger_name:
                continue
            
            # Find bill allocations within this ledger entry
            for bill_alloc in ledger_entry.findall(".//BILLALLOCATIONS.LIST"):
                bill_name = _text(bill_alloc, "NAME")
                amount = _num(bill_alloc, "AMOUNT")
                billtype = _text(bill_alloc, "BILLTYPE")
                bill_credit_period = _text(bill_alloc, "BILLCREDITPERIOD")
                
                # Normalize credit period to int
                credit_days = None
                if bill_credit_period:
                    try:
                        credit_days = int(str(bill_credit_period).strip())
                    except Exception:
                        credit_days = None
                
                # Only include if we have a bill name
                if bill_name:
                    out.append({
                        "voucher_guid": voucher_guid,
                        "voucher_date": voucher_date,
                        "voucher_type": voucher_type,
                        "voucher_number": voucher_number,
                        "reference_number": reference_number,
                        "reference_date": reference_date,
                        "narration": narration,
                        "party_name": party_name,
                        "place_of_supply": place_of_supply,
                        "is_invoice": is_invoice,
                        "is_accounting_voucher": is_accounting_voucher,
                        "is_inventory_voucher": is_inventory_voucher,
                        "is_order_voucher": is_order_voucher,
                        "alter_id": alter_id,
                        "ledger": ledger_name.strip(),
                        "bill_name": bill_name.strip(),
                        "amount": round(amount, 2),
                        "billtype": billtype or "",
                        "bill_credit_period": credit_days,
                    })
    
    return out




