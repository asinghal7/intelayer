"""
Parsers for Tally master data.

Each parser function takes XML text and returns a list of dictionaries
containing the parsed data ready for database insertion.
"""
from __future__ import annotations
from typing import Generator
from lxml import etree
from .base import (
    TallyXMLParser,
    sanitize_xml,
    text,
    attr,
    parse_tally_date,
    parse_float,
    parse_bool,
    parse_int,
    extract_alter_id,
)
from loguru import logger


def parse_company(xml_text: str) -> list[dict]:
    """
    Parse company master from Tally XML.
    
    Returns list with single company dict (or empty list if parse fails).
    
    TDL report output has fields directly under ENVELOPE when using XMLTAG.
    """
    parser = TallyXMLParser(xml_text)
    companies = []
    
    # For TDL reports with XMLTAG, fields are directly under ENVELOPE
    # Check if ENVELOPE has NAME child (indicates flat structure)
    root = parser.root
    name_elem = root.find("NAME")
    
    if name_elem is not None and name_elem.text:
        # Flat structure - fields directly under ENVELOPE
        company = {
            "guid": text(root, "GUID"),
            "alter_id": extract_alter_id(root),
            "name": text(root, "NAME"),
            "formal_name": text(root, "FORMALNAME"),
            "address": text(root, "ADDRESS"),
            "state": text(root, "STATENAME"),
            "country": text(root, "COUNTRYNAME"),
            "pincode": text(root, "PINCODE"),
            "email": text(root, "EMAIL"),
            "phone": text(root, "PHONE") or text(root, "PHONENUMBER"),
            "website": text(root, "WEBSITE"),
            "currency_name": text(root, "CURRENCYNAME") or text(root, "BASECURRENCYNAME"),
            "currency_symbol": text(root, "CURRENCYSYMBOL"),
            "financial_year_from": parse_tally_date(text(root, "STARTINGFROM")),
            "financial_year_to": parse_tally_date(text(root, "ENDINGAT")),
            "books_from": parse_tally_date(text(root, "BOOKSFROM")),
            "is_security_on": parse_bool(text(root, "ISSECURITYON")),
            "is_tally_audit_on": parse_bool(text(root, "ISTALLYAUDITON")),
        }
        if company.get("name"):
            companies.append(company)
    else:
        # Try nested structure paths
        paths = [
            ".//COMPANY",
            ".//TALLYMESSAGE/COMPANY",
        ]
        
        for path in paths:
            for elem in parser.find_all(path):
                company = {
                    "guid": attr(elem, "GUID") or text(elem, "GUID"),
                    "alter_id": extract_alter_id(elem),
                    "name": attr(elem, "NAME") or text(elem, "NAME"),
                    "formal_name": text(elem, "FORMALNAME"),
                    "address": text(elem, "ADDRESS"),
                    "state": text(elem, "STATENAME"),
                    "country": text(elem, "COUNTRYNAME"),
                    "pincode": text(elem, "PINCODE"),
                    "email": text(elem, "EMAIL"),
                    "phone": text(elem, "PHONE") or text(elem, "PHONENUMBER"),
                    "website": text(elem, "WEBSITE"),
                    "currency_name": text(elem, "CURRENCYNAME") or text(elem, "BASECURRENCYNAME"),
                    "currency_symbol": text(elem, "CURRENCYSYMBOL"),
                    "financial_year_from": parse_tally_date(text(elem, "STARTINGFROM")),
                    "financial_year_to": parse_tally_date(text(elem, "ENDINGAT")),
                    "books_from": parse_tally_date(text(elem, "BOOKSFROM")),
                    "is_security_on": parse_bool(text(elem, "ISSECURITYON")),
                    "is_tally_audit_on": parse_bool(text(elem, "ISTALLYAUDITON")),
                }
                if company.get("name"):
                    companies.append(company)
    
    logger.debug(f"Parsed {len(companies)} companies")
    return companies


def _parse_tdl_records(xml_text: str, record_identifier: str = "NAME") -> list[etree._Element]:
    """
    Parse TDL report output which may have flat structure.
    
    TDL reports with XMLTAG output records as siblings under ENVELOPE.
    Each record starts when we see a NAME element (or other identifier).
    
    Returns list of pseudo-elements containing grouped fields.
    """
    from lxml import etree as ET
    from copy import deepcopy
    
    sanitized = sanitize_xml(xml_text)
    root = ET.fromstring(sanitized.encode("utf-8"))
    
    # If there's a COLLECTION or DATA wrapper, look inside it
    collection = root.find(".//COLLECTION")
    if collection is not None:
        root = collection
    
    data = root.find(".//DATA")
    if data is not None:
        root = data
    
    # Get all direct children of root
    children = list(root)
    if not children:
        return []
    
    # Group children into records based on record_identifier
    # Use deepcopy to avoid modifying original tree structure
    records = []
    current_record = None
    
    for child in children:
        if child.tag == record_identifier:
            # Start of a new record
            if current_record is not None:
                records.append(current_record)
            current_record = ET.Element("RECORD")
            # Use deepcopy to preserve original element
            current_record.append(deepcopy(child))
        elif current_record is not None:
            # Use deepcopy to preserve original element
            current_record.append(deepcopy(child))
    
    # Don't forget the last record
    if current_record is not None:
        records.append(current_record)
    
    return records


def parse_groups(xml_text: str) -> list[dict]:
    """
    Parse ledger groups from Tally XML.
    
    Groups have hierarchical relationships via PARENT field.
    """
    parser = TallyXMLParser(xml_text)
    groups = []
    
    # First try TDL flat structure
    records = _parse_tdl_records(xml_text, "NAME")
    
    for elem in records:
        name = text(elem, "NAME")
        if not name:
            continue
        
        group = {
            "guid": text(elem, "GUID"),
            "alter_id": extract_alter_id(elem),
            "name": name,
            "name_lower": name.lower() if name else None,
            "parent": text(elem, "PARENT"),
            "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
            "primary_group": text(elem, "PRIMARYGROUP") or text(elem, "PARENT"),
            "is_revenue": parse_bool(text(elem, "ISREVENUE")),
            "is_deemed_positive": parse_bool(text(elem, "ISDEEMEDPOSITIVE")),
            "is_subledger": parse_bool(text(elem, "ISSUBLEDGER")),
            "affects_gross_profit": parse_bool(text(elem, "AFFECTSGROSSPROFIT")),
            "sort_position": parse_int(text(elem, "SORTPOSITION")),
            "nature_of_group": text(elem, "NATUREOFGROUP"),
        }
        groups.append(group)
    
    # If no TDL records found, try traditional structure
    if not groups:
        paths = [
            ".//GROUP",
            ".//TALLYMESSAGE/GROUP",
            ".//COLLECTION/GROUP",
        ]
        
        for path in paths:
            for elem in parser.find_all(path):
                name = attr(elem, "NAME") or text(elem, "NAME")
                if not name:
                    continue
                
                group = {
                    "guid": attr(elem, "GUID") or text(elem, "GUID"),
                    "alter_id": extract_alter_id(elem),
                    "name": name,
                    "name_lower": name.lower() if name else None,
                    "parent": text(elem, "PARENT"),
                    "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
                    "primary_group": text(elem, "PRIMARYGROUP") or text(elem, "PARENT"),
                    "is_revenue": parse_bool(text(elem, "ISREVENUE")),
                    "is_deemed_positive": parse_bool(text(elem, "ISDEEMEDPOSITIVE")),
                    "is_subledger": parse_bool(text(elem, "ISSUBLEDGER")),
                    "affects_gross_profit": parse_bool(text(elem, "AFFECTSGROSSPROFIT")),
                    "sort_position": parse_int(text(elem, "SORTPOSITION")),
                    "nature_of_group": text(elem, "NATUREOFGROUP"),
                }
                groups.append(group)
    
    logger.debug(f"Parsed {len(groups)} groups")
    return groups


def parse_ledgers(xml_text: str) -> tuple[list[dict], list[dict]]:
    """
    Parse ledgers from Tally XML.
    
    Returns tuple of (ledgers, opening_bills) where opening_bills are
    extracted from LEDGERBILLALLOCATIONS within ledger elements.
    """
    from pathlib import Path
    debug_file = Path("debug_ledgers_full_response.xml")
    debug_file.write_text(xml_text, encoding="utf-8")
    logger.info(f"DEBUG: Saved full XML to {debug_file}")
    
    parser = TallyXMLParser(xml_text)
    ledgers = []
    opening_bills = []
    
    # First try TDL flat structure
    records = _parse_tdl_records(xml_text, "NAME")
    
    for elem in records:
        name = text(elem, "NAME")
        if not name:
            continue
        
        ledger = {
            "guid": text(elem, "GUID"),
            "alter_id": extract_alter_id(elem),
            "name": name,
            "name_lower": name.lower() if name else None,
            "parent": text(elem, "PARENT"),
            "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
            "primary_group": text(elem, "PRIMARYGROUP"),
            # Classification
            "is_revenue": parse_bool(text(elem, "ISREVENUE")),
            "is_deemed_positive": parse_bool(text(elem, "ISDEEMEDPOSITIVE")),
            "is_bill_wise_on": parse_bool(text(elem, "ISBILLWISEON")),
            "is_cost_centres_on": parse_bool(text(elem, "ISCOSTCENTRESON")),
            # Balances
            "opening_balance": parse_float(text(elem, "OPENINGBALANCE")),
            "closing_balance": parse_float(text(elem, "CLOSINGBALANCE")),
            # GST
            "gstin": text(elem, "GSTIN"),
            "gst_registration_type": text(elem, "GSTREGISTRATIONTYPE"),
            "party_gstin": text(elem, "PARTYGSTIN"),
            "state_name": text(elem, "STATENAME"),
            "country_name": text(elem, "COUNTRYNAME"),
            # Contact
            "address": text(elem, "ADDRESS"),
            "pincode": text(elem, "PINCODE"),
            "email": text(elem, "EMAIL"),
            "phone": text(elem, "PHONE"),
            "contact_person": text(elem, "CONTACTPERSON"),
            # Banking
            "bank_name": text(elem, "BANKNAME"),
            "bank_branch": text(elem, "BANKBRANCHNAME"),
            "bank_account_number": text(elem, "BANKACCOUNTNUMBER"),
            "bank_ifsc": text(elem, "IFSCODE"),
            # Credit
            "credit_period": parse_int(text(elem, "CREDITPERIOD")),
            "credit_limit": parse_float(text(elem, "CREDITLIMIT")),
            # Tax
            "pan": text(elem, "PAN"),
            "income_tax_number": text(elem, "INCOMETAXNUMBER"),
            "tds_applicable": parse_bool(text(elem, "ISTDSAPPLICABLE")),
            "tcs_applicable": parse_bool(text(elem, "ISTCSAPPLICABLE")),
            # Mailing
            "mailing_name": text(elem, "MAILINGNAME"),
            "mailing_address": text(elem, "MAILINGADDRESS"),
            "mailing_state": text(elem, "MAILINGSTATE"),
            "mailing_country": text(elem, "MAILINGCOUNTRY"),
            "mailing_pincode": text(elem, "MAILINGPINCODE"),
        }
        ledgers.append(ledger)
    
    # If no TDL records found, try traditional structure
    if not ledgers:
        paths = [
            ".//LEDGER",
            ".//TALLYMESSAGE/LEDGER",
            ".//COLLECTION/LEDGER",
        ]
        
        for path in paths:
            for elem in parser.find_all(path):
                name = attr(elem, "NAME") or text(elem, "NAME")
                if not name:
                    continue
                
                ledger = {
                    "guid": attr(elem, "GUID") or text(elem, "GUID"),
                    "alter_id": extract_alter_id(elem),
                    "name": name,
                    "name_lower": name.lower() if name else None,
                    "parent": text(elem, "PARENT"),
                    "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
                    "primary_group": text(elem, "PRIMARYGROUP"),
                    # Classification
                    "is_revenue": parse_bool(text(elem, "ISREVENUE")),
                    "is_deemed_positive": parse_bool(text(elem, "ISDEEMEDPOSITIVE")),
                    "is_bill_wise_on": parse_bool(text(elem, "ISBILLWISEON")),
                    "is_cost_centres_on": parse_bool(text(elem, "ISCOSTCENTRESON")),
                    # Balances
                    "opening_balance": parse_float(text(elem, "OPENINGBALANCE")),
                    "closing_balance": parse_float(text(elem, "CLOSINGBALANCE")),
                    # GST
                    "gstin": text(elem, "GSTIN") or text(elem, "PARTYGSTIN"),
                    "gst_registration_type": text(elem, "GSTREGISTRATIONTYPE"),
                    "party_gstin": text(elem, "PARTYGSTIN"),
                    "state_name": text(elem, "STATENAME"),
                    "country_name": text(elem, "COUNTRYNAME"),
                    # Contact
                    "address": _join_address(elem),
                    "pincode": text(elem, "PINCODE"),
                    "email": text(elem, "EMAIL"),
                    "phone": text(elem, "LEDGERPHONE") or text(elem, "PHONE"),
                    "contact_person": text(elem, "LEDGERCONTACT") or text(elem, "CONTACTPERSON"),
                    # Banking
                    "bank_name": text(elem, "BANKNAME"),
                    "bank_branch": text(elem, "BANKBRANCHNAME"),
                    "bank_account_number": text(elem, "BANKACCOUNTNUMBER"),
                    "bank_ifsc": text(elem, "IFSCODE"),
                    # Credit
                    "credit_period": parse_int(text(elem, "CREDITPERIOD")),
                    "credit_limit": parse_float(text(elem, "CREDITLIMIT")),
                    # Tax
                    "pan": text(elem, "PAN") or text(elem, "PANNUMBER") or text(elem, "INCOMETAXNUMBER"),
                    "income_tax_number": text(elem, "INCOMETAXNUMBER"),
                    "tds_applicable": parse_bool(text(elem, "ISTDSAPPLICABLE")),
                    "tcs_applicable": parse_bool(text(elem, "ISTCSAPPLICABLE")),
                    # Mailing
                    "mailing_name": text(elem, "MAILINGNAME"),
                    "mailing_address": text(elem, "MAILINGADDRESS"),
                    "mailing_state": text(elem, "MAILINGSTATE"),
                    "mailing_country": text(elem, "MAILINGCOUNTRY"),
                    "mailing_pincode": text(elem, "MAILINGPINCODE"),
                }
                ledgers.append(ledger)
                
                # Extract opening bill allocations (only in traditional structure)
                for bill in elem.findall(".//LEDGERBILLALLOCATIONS.LIST"):
                    bill_name = text(bill, "NAME") or text(bill, "BILLNAME")
                    if bill_name:
                        opening_bills.append({
                            "ledger": name,
                            "ledger_lower": name.lower() if name else None,
                            "name": bill_name,
                            "bill_date": parse_tally_date(text(bill, "BILLDATE")),
                            "opening_balance": parse_float(text(bill, "OPENINGBALANCE") or text(bill, "AMOUNT")),
                            "bill_credit_period": parse_int(text(bill, "BILLCREDITPERIOD")),
                            "is_advance": parse_bool(text(bill, "ISADVANCE")),
                        })
    
    logger.debug(f"Parsed {len(ledgers)} ledgers with {len(opening_bills)} opening bills")
    return ledgers, opening_bills


def _join_address(elem: etree._Element) -> str | None:
    """Join multi-line address elements."""
    # Try single ADDRESS field
    single = text(elem, "ADDRESS")
    if single:
        return single
    
    # Try ADDRESS.LIST
    parts = []
    for addr_list in elem.findall(".//ADDRESS.LIST"):
        for addr in addr_list.findall("ADDRESS"):
            if addr.text:
                parts.append(addr.text.strip())
    
    return "\n".join(parts) if parts else None


def parse_stock_groups(xml_text: str) -> list[dict]:
    """Parse stock groups from Tally XML."""
    parser = TallyXMLParser(xml_text)
    items = []
    
    # First try TDL flat structure
    records = _parse_tdl_records(xml_text, "NAME")
    
    for elem in records:
        name = text(elem, "NAME")
        if not name:
            continue
        
        items.append({
            "guid": text(elem, "GUID"),
            "alter_id": extract_alter_id(elem),
            "name": name,
            "name_lower": name.lower() if name else None,
            "parent": text(elem, "PARENT"),
            "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
            "is_add_able": parse_bool(text(elem, "ISADDABLE"), default=True),
            "base_units": text(elem, "BASEUNITS"),
            "gst_applicable": text(elem, "GSTAPPLICABLE"),
        })
    
    # If no TDL records found, try traditional structure
    if not items:
        paths = [
            ".//STOCKGROUP",
            ".//TALLYMESSAGE/STOCKGROUP",
            ".//COLLECTION/STOCKGROUP",
        ]
        
        for path in paths:
            for elem in parser.find_all(path):
                name = attr(elem, "NAME") or text(elem, "NAME")
                if not name:
                    continue
                
                items.append({
                    "guid": attr(elem, "GUID") or text(elem, "GUID"),
                    "alter_id": extract_alter_id(elem),
                    "name": name,
                    "name_lower": name.lower() if name else None,
                    "parent": text(elem, "PARENT"),
                    "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
                    "is_add_able": parse_bool(text(elem, "ISADDABLE"), default=True),
                    "base_units": text(elem, "BASEUNITS"),
                    "gst_applicable": text(elem, "GSTAPPLICABLE"),
                })
    
    logger.debug(f"Parsed {len(items)} stock groups")
    return items


def parse_stock_categories(xml_text: str) -> list[dict]:
    """Parse stock categories from Tally XML."""
    parser = TallyXMLParser(xml_text)
    items = []
    
    # First try TDL flat structure
    records = _parse_tdl_records(xml_text, "NAME")
    
    for elem in records:
        name = text(elem, "NAME")
        if not name:
            continue
        
        items.append({
            "guid": text(elem, "GUID"),
            "alter_id": extract_alter_id(elem),
            "name": name,
            "name_lower": name.lower() if name else None,
            "parent": text(elem, "PARENT"),
            "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
        })
    
    # If no TDL records found, try traditional structure
    if not items:
        paths = [
            ".//STOCKCATEGORY",
            ".//TALLYMESSAGE/STOCKCATEGORY",
            ".//COLLECTION/STOCKCATEGORY",
        ]
        
        for path in paths:
            for elem in parser.find_all(path):
                name = attr(elem, "NAME") or text(elem, "NAME")
                if not name:
                    continue
                
                items.append({
                    "guid": attr(elem, "GUID") or text(elem, "GUID"),
                    "alter_id": extract_alter_id(elem),
                    "name": name,
                    "name_lower": name.lower() if name else None,
                    "parent": text(elem, "PARENT"),
                    "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
                })
    
    logger.debug(f"Parsed {len(items)} stock categories")
    return items


def parse_units(xml_text: str) -> list[dict]:
    """Parse units of measurement from Tally XML."""
    parser = TallyXMLParser(xml_text)
    items = []
    
    # First try TDL flat structure
    records = _parse_tdl_records(xml_text, "NAME")
    
    for elem in records:
        name = text(elem, "NAME")
        if not name:
            continue
        
        items.append({
            "guid": text(elem, "GUID"),
            "alter_id": extract_alter_id(elem),
            "name": name,
            "name_lower": name.lower() if name else None,
            "original_name": text(elem, "ORIGINALNAME"),
            "is_simple_unit": parse_bool(text(elem, "ISSIMPLEUNIT"), default=True),
            "base_units": text(elem, "BASEUNITS"),
            "additional_units": text(elem, "ADDITIONALUNITS"),
            "conversion": parse_float(text(elem, "CONVERSION")),
            "decimal_places": parse_int(text(elem, "DECIMALPLACES"), default=2),
            "is_gst_excluded": parse_bool(text(elem, "ISGSTEXCLUDED")),
        })
    
    # If no TDL records found, try traditional structure
    if not items:
        paths = [
            ".//UNIT",
            ".//TALLYMESSAGE/UNIT",
            ".//COLLECTION/UNIT",
        ]
        
        for path in paths:
            for elem in parser.find_all(path):
                name = attr(elem, "NAME") or text(elem, "NAME")
                if not name:
                    continue
                
                items.append({
                    "guid": attr(elem, "GUID") or text(elem, "GUID"),
                    "alter_id": extract_alter_id(elem),
                    "name": name,
                    "name_lower": name.lower() if name else None,
                    "original_name": text(elem, "ORIGINALNAME"),
                    "is_simple_unit": parse_bool(text(elem, "ISSIMPLEUNIT"), default=True),
                    "base_units": text(elem, "BASEUNITS"),
                    "additional_units": text(elem, "ADDITIONALUNITS"),
                    "conversion": parse_float(text(elem, "CONVERSION")),
                    "decimal_places": parse_int(text(elem, "DECIMALPLACES"), default=2),
                    "is_gst_excluded": parse_bool(text(elem, "ISGSTEXCLUDED")),
                })
    
    logger.debug(f"Parsed {len(items)} units")
    return items


def parse_godowns(xml_text: str) -> list[dict]:
    """Parse godowns (warehouses) from Tally XML."""
    parser = TallyXMLParser(xml_text)
    items = []
    
    # First try TDL flat structure
    records = _parse_tdl_records(xml_text, "NAME")
    
    for elem in records:
        name = text(elem, "NAME")
        if not name:
            continue
        
        items.append({
            "guid": text(elem, "GUID"),
            "alter_id": extract_alter_id(elem),
            "name": name,
            "name_lower": name.lower() if name else None,
            "parent": text(elem, "PARENT"),
            "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
            "address": text(elem, "ADDRESS"),
            "is_internal": parse_bool(text(elem, "ISINTERNAL")),
            "has_no_space": parse_bool(text(elem, "HASNOSPACE")),
        })
    
    # If no TDL records found, try traditional structure
    if not items:
        paths = [
            ".//GODOWN",
            ".//TALLYMESSAGE/GODOWN",
            ".//COLLECTION/GODOWN",
        ]
        
        for path in paths:
            for elem in parser.find_all(path):
                name = attr(elem, "NAME") or text(elem, "NAME")
                if not name:
                    continue
                
                items.append({
                    "guid": attr(elem, "GUID") or text(elem, "GUID"),
                    "alter_id": extract_alter_id(elem),
                    "name": name,
                    "name_lower": name.lower() if name else None,
                    "parent": text(elem, "PARENT"),
                    "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
                    "address": text(elem, "ADDRESS"),
                    "is_internal": parse_bool(text(elem, "ISINTERNAL")),
                    "has_no_space": parse_bool(text(elem, "HASNOSPACE")),
                })
    
    logger.debug(f"Parsed {len(items)} godowns")
    return items


def parse_stock_items(xml_text: str) -> list[dict]:
    """Parse stock items from Tally XML."""
    parser = TallyXMLParser(xml_text)
    items = []
    
    # First try TDL flat structure
    records = _parse_tdl_records(xml_text, "NAME")
    
    for elem in records:
        name = text(elem, "NAME")
        if not name:
            continue
        
        items.append({
            "guid": text(elem, "GUID"),
            "alter_id": extract_alter_id(elem),
            "name": name,
            "name_lower": name.lower() if name else None,
            "parent": text(elem, "PARENT"),
            "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
            "category": text(elem, "CATEGORY"),
            "category_lower": text(elem, "CATEGORY").lower() if text(elem, "CATEGORY") else None,
            "base_units": text(elem, "BASEUNITS"),
            # Identification
            "alias": text(elem, "ALIAS"),
            "part_number": text(elem, "PARTNUMBER"),
            "hsn_code": text(elem, "HSNCODE"),
            "description": text(elem, "DESCRIPTION"),
            "narration": text(elem, "NARRATION"),
            # Opening balances
            "opening_balance": parse_float(text(elem, "OPENINGBALANCE")),
            "opening_value": parse_float(text(elem, "OPENINGVALUE")),
            "opening_rate": parse_float(text(elem, "OPENINGRATE")),
            # Closing balances
            "closing_balance": parse_float(text(elem, "CLOSINGBALANCE")),
            "closing_value": parse_float(text(elem, "CLOSINGVALUE")),
            "closing_rate": parse_float(text(elem, "CLOSINGRATE")),
            # Pricing
            "standard_cost": parse_float(text(elem, "STANDARDCOST")),
            "standard_price": parse_float(text(elem, "STANDARDPRICE")),
            # GST
            "gst_applicable": text(elem, "GSTAPPLICABLE"),
            "gst_type_of_supply": text(elem, "GSTTYPEOFSUPPLY"),
            "is_reverse_charge_applicable": parse_bool(text(elem, "ISREVERSECHARGEAPPLICABLE")),
            # Classification
            "is_batch_wise_on": parse_bool(text(elem, "ISBATCHWISEON")),
            "is_perishable_on": parse_bool(text(elem, "ISPERISHABLEON")),
            "is_expiry_on": parse_bool(text(elem, "ISEXPIRYAPPLICABLE")),
            # Costing
            "costing_method": text(elem, "COSTINGMETHOD"),
            "valuation_method": text(elem, "VALUATIONMETHOD"),
            # Additional
            "ignore_negative_stock": parse_bool(text(elem, "IGNORENEGATIVESTOCK")),
            "ignore_physical_difference": parse_bool(text(elem, "IGNOREPHYSICALDIFFERENCE")),
            "treat_sales_as_manufactured": parse_bool(text(elem, "TREATSALESASMANUFACTURED")),
            "treat_purchases_as_consumed": parse_bool(text(elem, "TREATPURCHASESASCONSUMED")),
            "treat_rejects_as_scrap": parse_bool(text(elem, "TREATREJECTSASSCRAP")),
        })
    
    # If no TDL records found, try traditional structure
    if not items:
        paths = [
            ".//STOCKITEM",
            ".//TALLYMESSAGE/STOCKITEM",
            ".//COLLECTION/STOCKITEM",
        ]
        
        for path in paths:
            for elem in parser.find_all(path):
                name = attr(elem, "NAME") or text(elem, "NAME")
                if not name:
                    continue
                
                items.append({
                    "guid": attr(elem, "GUID") or text(elem, "GUID"),
                    "alter_id": extract_alter_id(elem),
                    "name": name,
                    "name_lower": name.lower() if name else None,
                    "parent": text(elem, "PARENT"),
                    "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
                    "category": text(elem, "CATEGORY"),
                    "category_lower": text(elem, "CATEGORY").lower() if text(elem, "CATEGORY") else None,
                    "base_units": text(elem, "BASEUNITS"),
                    # Identification
                    "alias": text(elem, "ALIAS"),
                    "part_number": text(elem, "PARTNUMBER"),
                    "hsn_code": text(elem, "HSNCODE") or text(elem, "GSTCLASSIFICATIONCODE"),
                    "description": text(elem, "DESCRIPTION"),
                    "narration": text(elem, "NARRATION"),
                    # Opening balances
                    "opening_balance": parse_float(text(elem, "OPENINGBALANCE")),
                    "opening_value": parse_float(text(elem, "OPENINGVALUE")),
                    "opening_rate": parse_float(text(elem, "OPENINGRATE")),
                    # Closing balances
                    "closing_balance": parse_float(text(elem, "CLOSINGBALANCE")),
                    "closing_value": parse_float(text(elem, "CLOSINGVALUE")),
                    "closing_rate": parse_float(text(elem, "CLOSINGRATE")),
                    # Pricing
                    "standard_cost": parse_float(text(elem, "STANDARDCOST")),
                    "standard_price": parse_float(text(elem, "STANDARDPRICE")),
                    # GST
                    "gst_applicable": text(elem, "GSTAPPLICABLE"),
                    "gst_type_of_supply": text(elem, "GSTTYPEOFSUPPLY"),
                    "is_reverse_charge_applicable": parse_bool(text(elem, "ISREVERSECHARGEAPPLICABLE")),
                    # Classification
                    "is_batch_wise_on": parse_bool(text(elem, "ISBATCHWISEON")),
                    "is_perishable_on": parse_bool(text(elem, "ISPERISHABLEON")),
                    "is_expiry_on": parse_bool(text(elem, "ISEXPIRYAPPLICABLE")),
                    # Costing
                    "costing_method": text(elem, "COSTINGMETHOD"),
                    "valuation_method": text(elem, "VALUATIONMETHOD"),
                    # Additional
                    "ignore_negative_stock": parse_bool(text(elem, "IGNORENEGATIVESTOCK")),
                    "ignore_physical_difference": parse_bool(text(elem, "IGNOREPHYSICALDIFFERENCE")),
                    "treat_sales_as_manufactured": parse_bool(text(elem, "TREATSALESASMANUFACTURED")),
                    "treat_purchases_as_consumed": parse_bool(text(elem, "TREATPURCHASESASCONSUMED")),
                    "treat_rejects_as_scrap": parse_bool(text(elem, "TREATREJECTSASSCRAP")),
                })
    
    logger.debug(f"Parsed {len(items)} stock items")
    return items


def parse_cost_categories(xml_text: str) -> list[dict]:
    """Parse cost categories from Tally XML."""
    parser = TallyXMLParser(xml_text)
    items = []
    
    # First try TDL flat structure
    records = _parse_tdl_records(xml_text, "NAME")
    
    for elem in records:
        name = text(elem, "NAME")
        if not name:
            continue
        
        items.append({
            "guid": text(elem, "GUID"),
            "alter_id": extract_alter_id(elem),
            "name": name,
            "name_lower": name.lower() if name else None,
            "allocate_revenue": parse_bool(text(elem, "ALLOCATEREVENUE")),
            "allocate_non_revenue": parse_bool(text(elem, "ALLOCATENONREVENUE")),
        })
    
    # If no TDL records found, try traditional structure
    if not items:
        paths = [
            ".//COSTCATEGORY",
            ".//TALLYMESSAGE/COSTCATEGORY",
            ".//COLLECTION/COSTCATEGORY",
        ]
        
        for path in paths:
            for elem in parser.find_all(path):
                name = attr(elem, "NAME") or text(elem, "NAME")
                if not name:
                    continue
                
                items.append({
                    "guid": attr(elem, "GUID") or text(elem, "GUID"),
                    "alter_id": extract_alter_id(elem),
                    "name": name,
                    "name_lower": name.lower() if name else None,
                    "allocate_revenue": parse_bool(text(elem, "ALLOCATEREVENUE")),
                    "allocate_non_revenue": parse_bool(text(elem, "ALLOCATENONREVENUE")),
                })
    
    logger.debug(f"Parsed {len(items)} cost categories")
    return items


def parse_cost_centres(xml_text: str) -> list[dict]:
    """Parse cost centres from Tally XML."""
    parser = TallyXMLParser(xml_text)
    items = []
    
    # First try TDL flat structure
    records = _parse_tdl_records(xml_text, "NAME")
    
    for elem in records:
        name = text(elem, "NAME")
        if not name:
            continue
        
        items.append({
            "guid": text(elem, "GUID"),
            "alter_id": extract_alter_id(elem),
            "name": name,
            "name_lower": name.lower() if name else None,
            "parent": text(elem, "PARENT"),
            "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
            "category": text(elem, "CATEGORY"),
            "category_lower": text(elem, "CATEGORY").lower() if text(elem, "CATEGORY") else None,
            "is_revenue": parse_bool(text(elem, "ISREVENUE"), default=True),
            "email": text(elem, "EMAIL"),
        })
    
    # If no TDL records found, try traditional structure
    if not items:
        paths = [
            ".//COSTCENTRE",
            ".//TALLYMESSAGE/COSTCENTRE",
            ".//COLLECTION/COSTCENTRE",
        ]
        
        for path in paths:
            for elem in parser.find_all(path):
                name = attr(elem, "NAME") or text(elem, "NAME")
                if not name:
                    continue
                
                items.append({
                    "guid": attr(elem, "GUID") or text(elem, "GUID"),
                    "alter_id": extract_alter_id(elem),
                    "name": name,
                    "name_lower": name.lower() if name else None,
                    "parent": text(elem, "PARENT"),
                    "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
                    "category": text(elem, "CATEGORY"),
                    "category_lower": text(elem, "CATEGORY").lower() if text(elem, "CATEGORY") else None,
                    "is_revenue": parse_bool(text(elem, "ISREVENUE"), default=True),
                    "email": text(elem, "EMAIL"),
                })
    
    logger.debug(f"Parsed {len(items)} cost centres")
    return items


def parse_voucher_types(xml_text: str) -> list[dict]:
    """Parse voucher types from Tally XML."""
    parser = TallyXMLParser(xml_text)
    items = []
    
    # First try TDL flat structure
    records = _parse_tdl_records(xml_text, "NAME")
    
    for elem in records:
        name = text(elem, "NAME")
        if not name:
            continue
        
        items.append({
            "guid": text(elem, "GUID"),
            "alter_id": extract_alter_id(elem),
            "name": name,
            "name_lower": name.lower() if name else None,
            "parent": text(elem, "PARENT"),
            "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
            "numbering_method": text(elem, "NUMBERINGMETHOD"),
            "is_deemed_positive": parse_bool(text(elem, "ISDEEMEDPOSITIVE")),
            "affects_stock": parse_bool(text(elem, "AFFECTSSTOCK")),
            "is_active": parse_bool(text(elem, "ISACTIVE"), default=True),
            "is_invoice": parse_bool(text(elem, "ISINVOICE")),
            "is_accounting_voucher": parse_bool(text(elem, "ISACCOUNTINGVOUCHER")),
            "is_inventory_voucher": parse_bool(text(elem, "ISINVENTORYVOUCHER")),
            "is_order_voucher": parse_bool(text(elem, "ISORDERVOUCHER")),
            "is_optional": parse_bool(text(elem, "ISOPTIONAL")),
            "common_narration": parse_bool(text(elem, "COMMONNARRATION")),
            "use_ref_voucher_date": parse_bool(text(elem, "USEREFVOUCHERDATE")),
        })
    
    # If no TDL records found, try traditional structure
    if not items:
        paths = [
            ".//VOUCHERTYPE",
            ".//TALLYMESSAGE/VOUCHERTYPE",
            ".//COLLECTION/VOUCHERTYPE",
        ]
        
        for path in paths:
            for elem in parser.find_all(path):
                name = attr(elem, "NAME") or text(elem, "NAME")
                if not name:
                    continue
                
                items.append({
                    "guid": attr(elem, "GUID") or text(elem, "GUID"),
                    "alter_id": extract_alter_id(elem),
                    "name": name,
                    "name_lower": name.lower() if name else None,
                    "parent": text(elem, "PARENT"),
                    "parent_lower": text(elem, "PARENT").lower() if text(elem, "PARENT") else None,
                    "numbering_method": text(elem, "NUMBERINGMETHOD"),
                    "is_deemed_positive": parse_bool(text(elem, "ISDEEMEDPOSITIVE")),
                    "affects_stock": parse_bool(text(elem, "AFFECTSSTOCK")),
                    "is_active": parse_bool(text(elem, "ISACTIVE"), default=True),
                    "is_invoice": parse_bool(text(elem, "ISINVOICE")),
                    "is_accounting_voucher": parse_bool(text(elem, "ISACCOUNTINGVOUCHER")),
                    "is_inventory_voucher": parse_bool(text(elem, "ISINVENTORYVOUCHER")),
                    "is_order_voucher": parse_bool(text(elem, "ISORDERVOUCHER")),
                    "is_optional": parse_bool(text(elem, "ISOPTIONAL")),
                    "common_narration": parse_bool(text(elem, "COMMONNARRATION")),
                    "use_ref_voucher_date": parse_bool(text(elem, "USEREFVOUCHERDATE")),
                })
    
    logger.debug(f"Parsed {len(items)} voucher types")
    return items


def parse_currencies(xml_text: str) -> list[dict]:
    """Parse currencies from Tally XML."""
    parser = TallyXMLParser(xml_text)
    items = []
    
    # First try TDL flat structure
    records = _parse_tdl_records(xml_text, "NAME")
    
    for elem in records:
        name = text(elem, "NAME")
        if not name:
            continue
        
        items.append({
            "guid": text(elem, "GUID"),
            "alter_id": extract_alter_id(elem),
            "name": name,
            "name_lower": name.lower() if name else None,
            "original_name": text(elem, "ORIGINALNAME"),
            "iso_code": text(elem, "ISOCODE"),
            "formal_name": text(elem, "FORMALNAME"),
            "symbol": text(elem, "SYMBOL"),
            "suffix_symbol": text(elem, "SUFFIXSYMBOL"),
            "decimal_places": parse_int(text(elem, "DECIMALPLACES"), default=2),
            "decimal_symbol": text(elem, "DECIMALSYMBOL") or ".",
            "in_millions": parse_bool(text(elem, "INMILLIONS")),
        })
    
    # If no TDL records found, try traditional structure
    if not items:
        paths = [
            ".//CURRENCY",
            ".//TALLYMESSAGE/CURRENCY",
            ".//COLLECTION/CURRENCY",
        ]
        
        for path in paths:
            for elem in parser.find_all(path):
                name = attr(elem, "NAME") or text(elem, "NAME")
                if not name:
                    continue
                
                items.append({
                    "guid": attr(elem, "GUID") or text(elem, "GUID"),
                    "alter_id": extract_alter_id(elem),
                    "name": name,
                    "name_lower": name.lower() if name else None,
                    "original_name": text(elem, "ORIGINALNAME"),
                    "iso_code": text(elem, "ISOCODE"),
                    "formal_name": text(elem, "FORMALNAME"),
                    "symbol": text(elem, "SYMBOL"),
                    "suffix_symbol": text(elem, "SUFFIXSYMBOL"),
                    "decimal_places": parse_int(text(elem, "DECIMALPLACES"), default=2),
                    "decimal_symbol": text(elem, "DECIMALSYMBOL") or ".",
                    "in_millions": parse_bool(text(elem, "INMILLIONS")),
                })
    
    logger.debug(f"Parsed {len(items)} currencies")
    return items


def parse_opening_bill_allocations(xml_text: str) -> list[dict]:
    """
    Parse opening bill allocations from Tally "List of Accounts" export.
    
    This uses the XML response from "List of Accounts" with EXPLODEFLAG=Yes,
    which returns nested LEDGER elements with BILLALLOCATIONS.LIST children.
    
    The BILLALLOCATIONS.LIST contains:
    - NAME: Bill reference name
    - BILLDATE: Bill date
    - OPENINGBALANCE: Opening balance amount for this bill
    - BILLCREDITPERIOD: Credit period in days
    - ISADVANCE: Whether it's an advance
    
    Returns list of dicts with keys:
    - ledger: Ledger name
    - ledger_lower: Ledger name (lowercase)
    - name: Bill reference name
    - bill_date: Bill date
    - opening_balance: Opening balance amount
    - bill_credit_period: Credit period in days
    - is_advance: Whether it's an advance
    """
    sanitized = sanitize_xml(xml_text)
    root = etree.fromstring(sanitized.encode("utf-8"))
    
    out: list[dict] = []
    
    # Iterate Ledgers and their BILLALLOCATIONS children
    # The "List of Accounts" export returns <LEDGER NAME="..."> elements
    for ledger in root.findall(".//LEDGER"):
        ledger_name = ledger.get("NAME")
        if not ledger_name:
            continue
        
        # Look for bill allocations within this ledger
        # Try multiple possible element names
        bill_allocs = (
            ledger.findall(".//BILLALLOCATIONS.LIST") or
            ledger.findall(".//LEDGERBILLALLOCATIONS.LIST") or
            ledger.findall(".//OPENINGBILLALLOCATIONS.LIST")
        )
        
        for bill in bill_allocs:
            name = text(bill, "NAME")
            bill_date_str = text(bill, "BILLDATE")
            opening_balance = parse_float(text(bill, "OPENINGBALANCE"), default=0.0)
            bill_credit_period_str = text(bill, "BILLCREDITPERIOD")
            is_advance = parse_bool(text(bill, "ISADVANCE"))
            
            # Normalize credit period to int
            credit_days = None
            if bill_credit_period_str:
                credit_days = parse_int(bill_credit_period_str, default=None)
            
            # Parse bill date
            bill_date = parse_tally_date(bill_date_str) if bill_date_str else None
            
            # Only include if we have a bill name
            if name:
                out.append({
                    "ledger": ledger_name.strip(),
                    "ledger_lower": ledger_name.strip().lower(),
                    "name": name.strip(),
                    "bill_date": bill_date,
                    "opening_balance": round(opening_balance, 2),
                    "bill_credit_period": credit_days,
                    "is_advance": bool(is_advance),
                })
    
    logger.debug(f"Parsed {len(out)} opening bill allocations")
    return out

