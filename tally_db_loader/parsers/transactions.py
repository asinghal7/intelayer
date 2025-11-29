"""
Parsers for Tally transaction data.

Handles vouchers and all related entries:
- Accounting (ledger) entries
- Inventory entries
- Bill allocations
- Cost centre allocations
- Batch allocations
"""
from __future__ import annotations
from typing import Generator
from lxml import etree
from .base import (
    TallyXMLParser,
    text,
    attr,
    parse_tally_date,
    parse_float,
    parse_bool,
    parse_int,
    extract_alter_id,
)
from loguru import logger


def parse_vouchers(xml_text: str) -> dict:
    """
    Parse vouchers and all related entries from Tally XML.
    
    This is the main transaction parser that extracts:
    - Voucher headers
    - Accounting entries (ledger entries)
    - Inventory entries
    - Bill allocations
    - Cost centre allocations
    - Batch allocations
    
    Returns dict with keys:
    - vouchers: list of voucher header dicts
    - accounting: list of accounting entry dicts
    - inventory: list of inventory entry dicts
    - bills: list of bill allocation dicts
    - cost_centres: list of cost centre allocation dicts
    - batches: list of batch allocation dicts
    """
    parser = TallyXMLParser(xml_text)
    
    vouchers = []
    accounting = []
    inventory = []
    bills = []
    cost_centres = []
    batches = []
    
    # Find vouchers in various possible paths
    voucher_paths = [
        ".//VOUCHER",
        ".//TALLYMESSAGE/VOUCHER",
        ".//COLLECTION/VOUCHER",
    ]
    
    for path in voucher_paths:
        for elem in parser.find_all(path):
            guid = attr(elem, "GUID") or text(elem, "GUID")
            if not guid:
                # Generate a pseudo-GUID if missing
                vnum = attr(elem, "VCHNUMBER") or text(elem, "VCHNUMBER") or ""
                vtype = attr(elem, "VCHTYPE") or text(elem, "VCHTYPE") or ""
                vdate = text(elem, "DATE") or ""
                guid = f"{vtype}/{vnum}/{vdate}"
            
            voucher_type = attr(elem, "VCHTYPE") or text(elem, "VCHTYPE") or text(elem, "VOUCHERTYPENAME")
            
            voucher = {
                "guid": guid,
                "alter_id": extract_alter_id(elem),
                "voucher_type": voucher_type,
                "voucher_type_lower": voucher_type.lower() if voucher_type else None,
                "voucher_number": attr(elem, "VCHNUMBER") or text(elem, "VCHNUMBER") or text(elem, "VOUCHERNUMBER"),
                "reference_number": text(elem, "REFERENCENUMBER") or text(elem, "REFERENCE"),
                "date": parse_tally_date(text(elem, "DATE")),
                "reference_date": parse_tally_date(text(elem, "REFERENCEDATE")),
                "party_name": text(elem, "PARTYLEDGERNAME") or text(elem, "PARTYNAME"),
                "party_name_lower": None,
                "party_gstin": text(elem, "PARTYGSTIN") or text(elem, "BASICBUYERPARTYGSTIN"),
                "place_of_supply": text(elem, "PLACEOFSUPPLY") or text(elem, "STATENAME"),
                "consignee_name": text(elem, "BASICBUYERNAME") or text(elem, "CONSIGNEENAME"),
                "buyer_name": text(elem, "BASICBUYERNAME"),
                "amount": _extract_voucher_amount(elem),
                "gst_registration_type": text(elem, "GSTREGISTRATIONTYPE"),
                "invoice_delivery_notes": text(elem, "BASICDELIVERYNOTES"),
                "invoice_order_number": text(elem, "BASICORDERNUMBER") or text(elem, "BASICBUYERORDERNUM"),
                "invoice_order_date": parse_tally_date(text(elem, "BASICORDERDATE") or text(elem, "BASICBUYERORDERDATE")),
                "shipping_bill_number": text(elem, "BASICSHIPBILLNUM") or text(elem, "BASICSHIPDOCUMENTNUM"),
                "shipping_date": parse_tally_date(text(elem, "BASICSHIPDATE")),
                "port_code": text(elem, "BASICPORTCODE"),
                "is_invoice": parse_bool(attr(elem, "ISINVOICE") or text(elem, "ISINVOICE")),
                "is_accounting_voucher": parse_bool(attr(elem, "ISACCOUNTINGVOUCHER") or text(elem, "ISACCOUNTINGVOUCHER")),
                "is_inventory_voucher": parse_bool(attr(elem, "ISINVENTORYVOUCHER") or text(elem, "ISINVENTORYVOUCHER")),
                "is_order_voucher": parse_bool(attr(elem, "ISORDERVOUCHER") or text(elem, "ISORDERVOUCHER")),
                "is_cancelled": parse_bool(text(elem, "ISCANCELLED")),
                "is_optional": parse_bool(text(elem, "ISOPTIONAL")),
                "is_posted": parse_bool(text(elem, "ISPOSTDATED"), default=True),
                "narration": text(elem, "NARRATION"),
                "master_id": attr(elem, "MASTERID") or text(elem, "MASTERID"),
            }
            
            if voucher["party_name"]:
                voucher["party_name_lower"] = voucher["party_name"].lower()
            
            vouchers.append(voucher)
            
            # Parse accounting (ledger) entries
            accounting.extend(_parse_accounting_entries(elem, guid))
            
            # Parse inventory entries
            inventory.extend(_parse_inventory_entries(elem, guid))
            
            # Parse bill allocations (from all ledger entries)
            bills.extend(_parse_bill_allocations(elem, guid))
            
            # Parse cost centre allocations
            cost_centres.extend(_parse_cost_centre_allocations(elem, guid))
            
            # Parse batch allocations
            batches.extend(_parse_batch_allocations(elem, guid))
    
    logger.debug(
        f"Parsed {len(vouchers)} vouchers, {len(accounting)} accounting entries, "
        f"{len(inventory)} inventory entries, {len(bills)} bills, "
        f"{len(cost_centres)} cost centres, {len(batches)} batches"
    )
    
    return {
        "vouchers": vouchers,
        "accounting": accounting,
        "inventory": inventory,
        "bills": bills,
        "cost_centres": cost_centres,
        "batches": batches,
    }


def _extract_voucher_amount(elem: etree._Element) -> float:
    """Extract total amount from voucher, trying multiple sources."""
    # Try direct amount field
    amt = parse_float(text(elem, "AMOUNT"))
    if amt != 0:
        return amt
    
    # Try from first bill allocation
    for bill in elem.findall(".//BILLALLOCATIONS.LIST"):
        amt = parse_float(text(bill, "AMOUNT"))
        if amt != 0:
            return amt
    
    # Sum from ledger entries
    total = 0.0
    for le in elem.findall(".//LEDGERENTRIES.LIST"):
        total += parse_float(text(le, "AMOUNT"))
    for le in elem.findall(".//ALLLEDGERENTRIES.LIST"):
        total += parse_float(text(le, "AMOUNT"))
    
    return total


def _parse_accounting_entries(voucher: etree._Element, voucher_guid: str) -> list[dict]:
    """Parse accounting (ledger) entries from voucher."""
    entries = []
    
    # Check both LEDGERENTRIES.LIST and ALLLEDGERENTRIES.LIST
    for path in [".//LEDGERENTRIES.LIST", ".//ALLLEDGERENTRIES.LIST"]:
        for le in voucher.findall(path):
            ledger = text(le, "LEDGERNAME") or text(le, "NAME")
            if not ledger:
                continue
            
            entry = {
                "voucher_guid": voucher_guid,
                "ledger": ledger,
                "ledger_lower": ledger.lower() if ledger else None,
                "parent": text(le, "PARENT"),
                "amount": parse_float(text(le, "AMOUNT")),
                "is_party_ledger": parse_bool(text(le, "ISPARTYLEDGER")),
                "is_deemed_positive": parse_bool(text(le, "ISDEEMEDPOSITIVE")),
                "gst_class": text(le, "GSTCLASS"),
                "gst_tax_type": text(le, "GSTTAXTYPE"),
                "gst_rate_incl_cess": parse_float(text(le, "GSTRATEINCLESS")),
                "narration": text(le, "NARRATION"),
            }
            entries.append(entry)
    
    return entries


def _parse_inventory_entries(voucher: etree._Element, voucher_guid: str) -> list[dict]:
    """Parse inventory entries from voucher."""
    entries = []
    
    for path in [".//ALLINVENTORYENTRIES.LIST", ".//INVENTORYENTRIES.LIST"]:
        for inv in voucher.findall(path):
            stock_item = text(inv, "STOCKITEMNAME") or text(inv, "NAME")
            if not stock_item:
                continue
            
            entry = {
                "voucher_guid": voucher_guid,
                "stock_item": stock_item,
                "stock_item_lower": stock_item.lower() if stock_item else None,
                "godown": text(inv, "GODOWNNAME"),
                "godown_lower": text(inv, "GODOWNNAME").lower() if text(inv, "GODOWNNAME") else None,
                "tracking_number": text(inv, "TRACKINGNUMBER"),
                "order_number": text(inv, "ORDERNUMBER"),
                "order_due_date": parse_tally_date(text(inv, "ORDERDUEDATE")),
                "billed_qty": _parse_quantity(text(inv, "BILLEDQTY")),
                "actual_qty": _parse_quantity(text(inv, "ACTUALQTY")),
                "rate": parse_float(text(inv, "RATE")),
                "amount": parse_float(text(inv, "AMOUNT")),
                "discount": parse_float(text(inv, "DISCOUNT")),
                "batch_name": text(inv, "BATCHNAME"),
                "narration": text(inv, "NARRATION"),
            }
            entries.append(entry)
    
    return entries


def _parse_quantity(qty_str: str | None) -> float:
    """
    Parse Tally quantity string which may include unit suffix.
    E.g., "10 Nos" -> 10.0
    """
    if not qty_str:
        return 0.0
    
    # Remove unit suffix and parse
    import re
    match = re.match(r"([-\d.,]+)", qty_str.strip())
    if match:
        return parse_float(match.group(1))
    
    return 0.0


def _parse_bill_allocations(voucher: etree._Element, voucher_guid: str) -> list[dict]:
    """Parse bill allocations from all ledger entries in voucher."""
    bills = []
    
    # Bills can be nested under ledger entries or directly under voucher
    paths = [
        ".//LEDGERENTRIES.LIST//BILLALLOCATIONS.LIST",
        ".//ALLLEDGERENTRIES.LIST//BILLALLOCATIONS.LIST",
        ".//BILLALLOCATIONS.LIST",
    ]
    
    for path in paths:
        for bill in voucher.findall(path):
            name = text(bill, "NAME") or text(bill, "BILLNAME")
            if not name:
                continue
            
            # Try to get ledger from parent if nested
            ledger = _get_parent_ledger(bill)
            if not ledger:
                # Fall back to party ledger name from voucher
                ledger = text(voucher, "PARTYLEDGERNAME")
            
            entry = {
                "voucher_guid": voucher_guid,
                "ledger": ledger,
                "ledger_lower": ledger.lower() if ledger else None,
                "name": name,
                "bill_type": text(bill, "BILLTYPE") or "New Ref",
                "amount": parse_float(text(bill, "AMOUNT")),
                "bill_credit_period": parse_int(text(bill, "BILLCREDITPERIOD")),
            }
            bills.append(entry)
    
    return bills


def _get_parent_ledger(bill_elem: etree._Element) -> str | None:
    """Try to get ledger name from parent element."""
    # Walk up the tree to find LEDGERNAME
    parent = bill_elem.getparent()
    while parent is not None:
        ledger = text(parent, "LEDGERNAME")
        if ledger:
            return ledger
        parent = parent.getparent()
    return None


def _parse_cost_centre_allocations(voucher: etree._Element, voucher_guid: str) -> list[dict]:
    """Parse cost centre allocations from voucher."""
    allocations = []
    
    for path in [
        ".//LEDGERENTRIES.LIST//CATEGORYALLOCATIONS.LIST",
        ".//ALLLEDGERENTRIES.LIST//CATEGORYALLOCATIONS.LIST",
        ".//CATEGORYALLOCATIONS.LIST",
    ]:
        for cc in voucher.findall(path):
            cost_centre = text(cc, "COSTCENTRE") or text(cc, "NAME")
            if not cost_centre:
                continue
            
            entry = {
                "voucher_guid": voucher_guid,
                "accounting_id": None,  # Will be linked during load
                "cost_centre": cost_centre,
                "cost_centre_lower": cost_centre.lower() if cost_centre else None,
                "category": text(cc, "CATEGORY"),
                "category_lower": text(cc, "CATEGORY").lower() if text(cc, "CATEGORY") else None,
                "amount": parse_float(text(cc, "AMOUNT")),
            }
            allocations.append(entry)
    
    return allocations


def _parse_batch_allocations(voucher: etree._Element, voucher_guid: str) -> list[dict]:
    """Parse batch allocations from voucher inventory entries."""
    batches = []
    
    for path in [
        ".//ALLINVENTORYENTRIES.LIST//BATCHALLOCATIONS.LIST",
        ".//INVENTORYENTRIES.LIST//BATCHALLOCATIONS.LIST",
    ]:
        for batch in voucher.findall(path):
            batch_name = text(batch, "BATCHNAME") or text(batch, "NAME")
            if not batch_name:
                continue
            
            # Get parent stock item
            parent_inv = batch.getparent()
            while parent_inv is not None and parent_inv.tag not in (
                "ALLINVENTORYENTRIES.LIST", "INVENTORYENTRIES.LIST"
            ):
                parent_inv = parent_inv.getparent()
            
            stock_item = text(parent_inv, "STOCKITEMNAME") if parent_inv is not None else None
            godown = text(batch, "GODOWNNAME") or (text(parent_inv, "GODOWNNAME") if parent_inv is not None else None)
            
            entry = {
                "voucher_guid": voucher_guid,
                "inventory_id": None,  # Will be linked during load
                "stock_item": stock_item,
                "stock_item_lower": stock_item.lower() if stock_item else None,
                "godown": godown,
                "godown_lower": godown.lower() if godown else None,
                "batch_name": batch_name,
                "manufacturing_date": parse_tally_date(text(batch, "MFDON")),
                "expiry_date": parse_tally_date(text(batch, "EXPIRYDATE")),
                "billed_qty": _parse_quantity(text(batch, "BILLEDQTY")),
                "actual_qty": _parse_quantity(text(batch, "ACTUALQTY")),
                "amount": parse_float(text(batch, "AMOUNT")),
            }
            batches.append(entry)
    
    return batches


# Re-export individual parse functions for backwards compatibility
parse_accounting_entries = _parse_accounting_entries
parse_inventory_entries = _parse_inventory_entries
parse_bill_allocations = _parse_bill_allocations
parse_cost_centre_allocations = _parse_cost_centre_allocations
parse_batch_allocations = _parse_batch_allocations


def parse_closing_stock(xml_text: str, as_of_date=None) -> list[dict]:
    """
    Parse closing stock summary from Tally XML.
    
    Args:
        xml_text: XML response from closing stock request
        as_of_date: Date for the closing stock snapshot
        
    Returns:
        List of closing stock dicts
    """
    from datetime import date as dt_date
    
    parser = TallyXMLParser(xml_text)
    items = []
    
    as_of = as_of_date or dt_date.today()
    
    for path in [".//STOCKITEM", ".//TALLYMESSAGE/STOCKITEM", ".//COLLECTION/STOCKITEM"]:
        for elem in parser.find_all(path):
            name = attr(elem, "NAME") or text(elem, "NAME")
            if not name:
                continue
            
            # Check for batch-wise data
            batch_allocs = elem.findall(".//BATCHALLOCATIONS.LIST")
            
            if batch_allocs:
                # Godown/batch-wise closing
                for batch in batch_allocs:
                    godown = text(batch, "GODOWNNAME")
                    items.append({
                        "as_of_date": as_of,
                        "stock_item": name,
                        "stock_item_lower": name.lower() if name else None,
                        "godown": godown,
                        "godown_lower": godown.lower() if godown else None,
                        "closing_qty": parse_float(text(batch, "CLOSINGBALANCE")),
                        "closing_value": parse_float(text(batch, "CLOSINGVALUE")),
                        "closing_rate": parse_float(text(batch, "CLOSINGRATE")),
                    })
            else:
                # Simple closing
                items.append({
                    "as_of_date": as_of,
                    "stock_item": name,
                    "stock_item_lower": name.lower() if name else None,
                    "godown": None,
                    "godown_lower": None,
                    "closing_qty": parse_float(text(elem, "CLOSINGBALANCE")),
                    "closing_value": parse_float(text(elem, "CLOSINGVALUE")),
                    "closing_rate": parse_float(text(elem, "CLOSINGRATE")),
                })
    
    logger.debug(f"Parsed {len(items)} closing stock entries")
    return items

