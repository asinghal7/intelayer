"""
Parser for Tally Masters XML (Units, Stock Groups, Stock Items).
Handles both file-based and HTTP-fetched masters exports.
"""
from __future__ import annotations
from lxml import etree
from .validators import sanitize_xml


def _text(element: etree._Element | None, tag: str) -> str | None:
    """Safely extract text from an XML element, returning None for empty values."""
    if element is None:
        return None
    val = element.findtext(tag)
    if val is None:
        return None
    val = val.strip()
    return val if val else None


def _bool(element: etree._Element | None, tag: str) -> bool:
    """Extract boolean value from Yes/No text."""
    val = _text(element, tag)
    if val is None:
        return False
    return val.lower() in ("yes", "y", "true", "1")


def parse_units(xml_text: str) -> list[dict]:
    """
    Parse UNIT elements from Tally masters XML.
    
    Returns list of dicts with keys:
    - name: UOM name (e.g., "no.", "mtr")
    - guid: Tally GUID
    - original_name: Original/formal name (e.g., "Number", "Metre")
    - gst_rep_uom: GST reporting UOM (e.g., "PCS-PIECES", "MTR-METERS")
    - is_simple: Whether it's a simple unit
    - alter_id: Tally alteration ID
    """
    sanitized = sanitize_xml(xml_text)
    root = etree.fromstring(sanitized.encode("utf-8"))
    out: list[dict] = []
    
    for unit in root.findall(".//UNIT"):
        name = unit.get("NAME")
        if not name:
            continue
        
        guid = _text(unit, "GUID")
        original_name = _text(unit, "ORIGINALNAME")
        gst_rep_uom = _text(unit, "GSTREPUOM")
        is_simple = _bool(unit, "ISSIMPLEUNIT")
        
        # Get ALTERID (may have spaces)
        alter_id_str = _text(unit, "ALTERID")
        alter_id = None
        if alter_id_str:
            try:
                alter_id = int(alter_id_str.replace(" ", ""))
            except ValueError:
                pass
        
        out.append({
            "name": name.strip(),
            "guid": guid,
            "original_name": original_name,
            "gst_rep_uom": gst_rep_uom,
            "is_simple": is_simple,
            "alter_id": alter_id,
        })
    
    return out


def parse_stock_groups(xml_text: str) -> list[dict]:
    """
    Parse STOCKGROUP elements from Tally masters XML.
    
    Returns list of dicts with keys:
    - name: Stock group name
    - guid: Tally GUID
    - parent_name: Parent group name (None for root groups)
    - alter_id: Tally alteration ID
    """
    sanitized = sanitize_xml(xml_text)
    root = etree.fromstring(sanitized.encode("utf-8"))
    out: list[dict] = []
    
    for group in root.findall(".//STOCKGROUP"):
        name = group.get("NAME")
        if not name:
            continue
        
        guid = _text(group, "GUID")
        parent_name = _text(group, "PARENT")
        
        # Get ALTERID (may have spaces)
        alter_id_str = _text(group, "ALTERID")
        alter_id = None
        if alter_id_str:
            try:
                alter_id = int(alter_id_str.replace(" ", ""))
            except ValueError:
                pass
        
        out.append({
            "name": name.strip(),
            "guid": guid,
            "parent_name": parent_name,  # None for root groups
            "alter_id": alter_id,
        })
    
    return out


def parse_stock_items(xml_text: str) -> list[dict]:
    """
    Parse STOCKITEM elements from Tally masters XML (if present).
    
    Returns list of dicts with keys:
    - name: Stock item name
    - guid: Tally GUID
    - parent_name: Parent stock group name
    - base_units: Base unit of measurement
    - hsn: HSN code (if available)
    """
    sanitized = sanitize_xml(xml_text)
    root = etree.fromstring(sanitized.encode("utf-8"))
    out: list[dict] = []
    
    for item in root.findall(".//STOCKITEM"):
        name = item.get("NAME")
        if not name:
            continue
        
        guid = _text(item, "GUID")
        parent_name = _text(item, "PARENT")
        base_units = _text(item, "BASEUNITS")
        
        # Extract HSN code - prefer from HSNDETAILS.LIST
        hsn = None
        for hsn_detail in item.findall(".//HSNDETAILS.LIST"):
            hsn_code = _text(hsn_detail, "HSNCODE")
            if hsn_code:
                hsn = hsn_code
                break
        
        # Fallback to direct HSNCODE tag
        if not hsn:
            hsn = _text(item, "HSNCODE")
        
        out.append({
            "name": name.strip(),
            "guid": guid,
            "parent_name": parent_name,
            "base_units": base_units,
            "hsn": hsn,
        })
    
    return out


def parse_masters(xml_text: str) -> dict:
    """
    Parse all masters from a Tally XML export.
    
    Returns dict with keys:
    - units: list of unit dicts
    - groups: list of stock group dicts
    - items: list of stock item dicts
    """
    return {
        "units": parse_units(xml_text),
        "groups": parse_stock_groups(xml_text),
        "items": parse_stock_items(xml_text),
    }

