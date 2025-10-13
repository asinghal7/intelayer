from __future__ import annotations
from lxml import etree

class TallyHTTPError(RuntimeError):
    pass

def ensure_status_ok(xml_text: str) -> None:
    """
    Raises TallyHTTPError if <STATUS> is missing or not '1'.
    Some "empty" responses still have STATUS=1; that's OK (caller can treat it as no data).
    """
    try:
        root = etree.fromstring(xml_text.encode("utf-8"))
    except Exception as e:
        raise TallyHTTPError(f"Invalid XML from Tally: {e}") from e

    status = root.findtext(".//STATUS")
    # STATUS is usually '1' for success. If absent, assume OK (older builds),
    # but if present and not '1' → error.
    if status is not None and status.strip() != "1":
        # Try to extract an error message if present
        msg = root.findtext(".//LINEERROR") or root.findtext(".//ERROR")
        raise TallyHTTPError(f"Tally returned STATUS={status} {('- ' + msg) if msg else ''}")

