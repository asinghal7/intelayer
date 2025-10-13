from pathlib import Path
from adapters.tally_http.parser import parse_daybook

def test_parse_daybook_sample():
    xml = (Path(__file__).parent / "fixtures" / "daybook_sample.xml").read_text(encoding="utf-8")
    rows = parse_daybook(xml)
    assert len(rows) == 1
    r = rows[0]
    assert r["vchtype"] == "Sales"
    assert r["vchnumber"] == "S-101"
    assert r["party"] == "Acme Distributors"
    assert r["amount"] == 1234.50

