from __future__ import annotations
import re
from lxml import etree

class TallyHTTPError(RuntimeError):
    pass

def sanitize_xml(xml_string: str) -> str:
    """
    Sanitize XML string by removing invalid characters and character references.
    Tally often includes invalid control characters in XML output.
    """
    # First, remove invalid character entity references like &#x0; &#x1F; etc.
    # These are XML entities that reference invalid characters
    xml_string = re.sub(r'&#x([0-8bcefBCEF]|1[0-9a-fA-F]);', '', xml_string)
    xml_string = re.sub(r'&#([0-9]|1[0-9]|2[0-6]|3[01]);', '', xml_string)
    
    # Then remove raw invalid XML characters (control characters except tab, newline, carriage return)
    # Valid XML chars: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    invalid_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x84\x86-\x9F]')
    xml_string = invalid_chars.sub('', xml_string)
    
    return xml_string

def ensure_status_ok(xml_text: str) -> None:
    """
    Raises TallyHTTPError if <STATUS> is missing or not '1'.
    Some "empty" responses still have STATUS=1; that's OK (caller can treat it as no data).
    """
    try:
        # Sanitize XML to remove invalid characters before parsing
        sanitized = sanitize_xml(xml_text)
        root = etree.fromstring(sanitized.encode("utf-8"))
    except Exception as e:
        raise TallyHTTPError(f"Invalid XML from Tally: {e}") from e

    status = root.findtext(".//STATUS")
    # STATUS is usually '1' for success. If absent, assume OK (older builds),
    # but if present and not '1' → error.
    if status is not None and status.strip() != "1":
        # Try to extract an error message if present
        msg = root.findtext(".//LINEERROR") or root.findtext(".//ERROR")
        raise TallyHTTPError(f"Tally returned STATUS={status} {('- ' + msg) if msg else ''}")

