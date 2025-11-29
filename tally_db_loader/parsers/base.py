"""
Base utilities for XML parsing.

Provides common functions for parsing Tally XML responses including:
- XML sanitization
- Date parsing
- Numeric parsing
- Boolean parsing
"""
from __future__ import annotations
import re
from datetime import datetime, date
from typing import Optional, Any
from lxml import etree
from loguru import logger


def sanitize_xml(xml_text: str) -> str:
    """
    Remove invalid XML characters and fix common issues.
    
    Tally sometimes produces XML with control characters or invalid sequences.
    This function cleans those up for safe parsing.
    
    Based on Open Source tally db loader approach - strip invalid character references.
    """
    if not xml_text:
        return xml_text
    
    # Remove null bytes
    xml_text = xml_text.replace("\x00", "")
    
    # Remove invalid XML character references (&#0; through &#31; except &#9;, &#10;, &#13;)
    # This is the main fix for "xmlParseCharRef: invalid xmlChar value" errors
    # Tally outputs &#4; and similar invalid references
    def remove_invalid_char_refs(s: str) -> str:
        # Remove numeric character references for control chars (except tab, newline, CR)
        # &#0; through &#8;, &#11;, &#12;, &#14; through &#31;
        s = re.sub(r'&#([0-8]|1[0-2]|1[4-9]|2[0-9]|3[01]);', '', s)
        # Also handle hex form &#x0; through &#x1F; (except 9, A, D)
        # Match hex digits 0-8, B, C, E, F (case insensitive), and 10-1F
        s = re.sub(r'&#x([0-8bBcCeEfF]|1[0-9a-fA-F]);', '', s)
        return s
    
    xml_text = remove_invalid_char_refs(xml_text)
    
    # Remove other control characters (except tab, newline, carriage return)
    # XML 1.0 only allows #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD]
    def remove_control_chars(s: str) -> str:
        return "".join(
            c if (
                c in "\t\n\r" or
                0x20 <= ord(c) <= 0xD7FF or
                0xE000 <= ord(c) <= 0xFFFD
            ) else ""
            for c in s
        )
    
    xml_text = remove_control_chars(xml_text)
    
    # Fix common entity issues
    # Replace unescaped ampersands (but not valid entities)
    xml_text = re.sub(r"&(?!(amp|lt|gt|apos|quot|#\d+|#x[\da-fA-F]+);)", "&amp;", xml_text)
    
    return xml_text


def parse_tally_date(s: str | None) -> Optional[date]:
    """
    Parse Tally date string to Python date.
    
    Tally uses multiple date formats:
    - YYYYMMDD (most common)
    - YYYY-MM-DD
    - DD-MMM-YYYY (e.g., "01-Apr-2024")
    
    Returns None for empty or unparseable strings.
    """
    if not s:
        return None
    
    s = str(s).strip()
    if not s or s.lower() in ("", "null", "none"):
        return None
    
    # Try different formats
    formats = [
        "%Y%m%d",      # 20240401
        "%Y-%m-%d",    # 2024-04-01
        "%d-%b-%Y",    # 01-Apr-2024
        "%d/%m/%Y",    # 01/04/2024
        "%d-%m-%Y",    # 01-04-2024
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date: {s}")
    return None


def parse_float(s: str | None, default: float = 0.0) -> float:
    """
    Parse Tally numeric string to float.
    
    Handles:
    - Comma separators (1,234.56)
    - Parentheses for negatives ((1234.56))
    - Currency symbols
    - Empty strings
    """
    if not s:
        return default
    
    s = str(s).strip()
    if not s or s.lower() in ("", "null", "none"):
        return default
    
    # Check for parentheses (negative)
    is_negative = s.startswith("(") and s.endswith(")")
    if is_negative:
        s = s[1:-1]
    
    # Remove common non-numeric characters
    s = re.sub(r"[,₹$€£¥\s]", "", s)
    
    # Handle Dr/Cr suffixes
    if s.endswith(" Dr") or s.endswith("Dr"):
        s = s.replace(" Dr", "").replace("Dr", "")
    elif s.endswith(" Cr") or s.endswith("Cr"):
        s = s.replace(" Cr", "").replace("Cr", "")
        is_negative = not is_negative  # Credit is typically negative in accounting
    
    try:
        val = float(s)
        return -val if is_negative else val
    except ValueError:
        logger.warning(f"Could not parse float: {s}")
        return default


def parse_int(s: str | None, default: int = 0) -> int:
    """Parse Tally integer string."""
    if not s:
        return default
    
    s = str(s).strip().replace(",", "").replace(" ", "")
    if not s or s.lower() in ("", "null", "none"):
        return default
    
    try:
        return int(float(s))  # Handle "123.0" style
    except ValueError:
        logger.warning(f"Could not parse int: {s}")
        return default


def parse_bool(s: str | None, default: bool = False) -> bool:
    """
    Parse Tally boolean string.
    
    Tally uses various representations:
    - Yes/No
    - True/False
    - 1/0
    """
    if s is None:
        return default
    
    s = str(s).strip().lower()
    if s in ("yes", "true", "1", "y"):
        return True
    elif s in ("no", "false", "0", "n", ""):
        return False
    
    return default


def text(element: etree._Element | None, tag: str, default: str | None = None) -> str | None:
    """
    Safely extract text from XML element.
    
    Args:
        element: Parent XML element
        tag: Child tag name to find
        default: Default value if not found
        
    Returns:
        Stripped text content or default
    """
    if element is None:
        return default
    
    child = element.find(tag)
    if child is None or child.text is None:
        return default
    
    return child.text.strip() or default


def attr(element: etree._Element | None, name: str, default: str | None = None) -> str | None:
    """
    Safely extract attribute from XML element.
    
    Args:
        element: XML element
        name: Attribute name
        default: Default value if not found
        
    Returns:
        Attribute value or default
    """
    if element is None:
        return default
    
    val = element.get(name)
    if val is None:
        return default
    
    return val.strip() or default


class TallyXMLParser:
    """
    Base class for Tally XML parsers.
    
    Provides common utilities for parsing XML responses and
    extracting structured data.
    """
    
    def __init__(self, xml_text: str):
        """Initialize parser with XML text."""
        self.raw_xml = xml_text
        self.sanitized_xml = sanitize_xml(xml_text)
        self._root = None
    
    @property
    def root(self) -> etree._Element:
        """Get parsed XML root element."""
        if self._root is None:
            self._root = etree.fromstring(self.sanitized_xml.encode("utf-8"))
        return self._root
    
    def find_all(self, xpath: str) -> list[etree._Element]:
        """Find all elements matching xpath."""
        return self.root.findall(xpath)
    
    def find_one(self, xpath: str) -> etree._Element | None:
        """Find first element matching xpath."""
        return self.root.find(xpath)
    
    def text(self, element: etree._Element, tag: str, default: str | None = None) -> str | None:
        """Extract text from child element."""
        return text(element, tag, default)
    
    def attr(self, element: etree._Element, name: str, default: str | None = None) -> str | None:
        """Extract attribute from element."""
        return attr(element, name, default)
    
    def parse_date(self, s: str | None) -> Optional[date]:
        """Parse date string."""
        return parse_tally_date(s)
    
    def parse_float(self, s: str | None, default: float = 0.0) -> float:
        """Parse float string."""
        return parse_float(s, default)
    
    def parse_bool(self, s: str | None, default: bool = False) -> bool:
        """Parse boolean string."""
        return parse_bool(s, default)
    
    def parse_int(self, s: str | None, default: int = 0) -> int:
        """Parse integer string."""
        return parse_int(s, default)


def extract_alter_id(element: etree._Element) -> int | None:
    """
    Extract ALTERID from element, handling space-separated format.
    
    Tally sometimes formats ALTERID with spaces (e.g., "1 234" instead of "1234").
    """
    alter_id_text = text(element, "ALTERID")
    if not alter_id_text:
        alter_id_text = attr(element, "ALTERID")
    
    if not alter_id_text:
        return None
    
    # Remove spaces and parse
    try:
        return int(alter_id_text.replace(" ", "").replace(",", ""))
    except ValueError:
        return None

