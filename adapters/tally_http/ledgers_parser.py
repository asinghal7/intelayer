"""
Parser for Tally Ledgers XML.
Extracts ledger groups and ledgers with their parent relationships.
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


def parse_ledgers(xml_text: str) -> list[dict]:
    """
    Parse LEDGER elements from Tally XML.
    
    Returns list of dicts with keys:
    - name: Ledger name (e.g., customer name)
    - guid: Tally GUID
    - parent_name: Parent group name (e.g., "Sundry Debtors")
    - alter_id: Tally alteration ID
    """
    sanitized = sanitize_xml(xml_text)
    root = etree.fromstring(sanitized.encode("utf-8"))
    out: list[dict] = []
    
    for ledger in root.findall(".//LEDGER"):
        name = ledger.get("NAME")
        if not name:
            continue
        
        guid = _text(ledger, "GUID")
        parent_name = _text(ledger, "PARENT")
        
        # Get ALTERID (may have spaces)
        alter_id_str = _text(ledger, "ALTERID")
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


def parse_ledger_groups(xml_text: str) -> list[dict]:
    """
    Parse GROUP elements from Tally XML to get ledger group hierarchy.
    
    Returns list of dicts with keys:
    - name: Group name
    - guid: Tally GUID
    - parent_name: Parent group name (None for root groups)
    - alter_id: Tally alteration ID
    """
    sanitized = sanitize_xml(xml_text)
    root = etree.fromstring(sanitized.encode("utf-8"))
    out: list[dict] = []
    
    for group in root.findall(".//GROUP"):
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
            "parent_name": parent_name,
            "alter_id": alter_id,
        })
    
    return out


def extract_ledger_groups_from_ledgers(ledgers: list[dict]) -> list[dict]:
    """
    Extract unique ledger groups from ledger parent names.
    This is used when we only have ledger data without explicit group definitions.
    
    Args:
        ledgers: List of ledger dicts with parent_name
        
    Returns:
        List of unique groups with their hierarchies
    """
    # Collect all unique parent names
    group_names = set()
    for ledger in ledgers:
        if ledger.get("parent_name"):
            group_names.add(ledger["parent_name"])
    
    # Build group hierarchy by checking if parent is also a ledger
    ledger_names = {ledger["name"] for ledger in ledgers}
    
    groups = []
    for group_name in group_names:
        # Check if this group is also a ledger (indicating sub-group)
        # If it's a ledger, its parent is the parent of this group
        parent_of_group = None
        for ledger in ledgers:
            if ledger["name"] == group_name:
                parent_of_group = ledger.get("parent_name")
                break
        
        groups.append({
            "name": group_name,
            "guid": None,  # Not available from ledger data alone
            "parent_name": parent_of_group,
            "alter_id": None,
        })
    
    return groups


def parse_ledger_masters(xml_text: str) -> dict:
    """
    Parse all ledger-related data from a Tally XML export.
    
    Returns dict with keys:
    - groups: list of ledger group dicts
    - ledgers: list of ledger dicts
    """
    groups = parse_ledger_groups(xml_text)
    ledgers = parse_ledgers(xml_text)
    
    # If no explicit groups found, extract from ledger parents
    if not groups and ledgers:
        groups = extract_ledger_groups_from_ledgers(ledgers)
    
    return {
        "groups": groups,
        "ledgers": ledgers,
    }

