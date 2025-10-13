from pathlib import Path
from adapters.tally_http.parser import parse_daybook

def test_amount_from_party_line_signed():
    xml = (Path(__file__).parent / "fixtures" / "daybook_header_empty_with_lines.xml").read_text(encoding="utf-8")
    rows = parse_daybook(xml)
    assert len(rows) == 1
    r = rows[0]
    assert r["vchtype"] == "Sales"
    assert r["vchnumber"] == "S-200"
    assert r["party"] == "Acme Distributors"
    # Should pick party ledger line with sign preserved (Sales -> customer debit -> +)
    assert r["amount"] == 1234.50

