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

def test_parse_daybook_with_customer_details():
    xml = (Path(__file__).parent / "fixtures" / "daybook_with_customer_details.xml").read_text(encoding="utf-8")
    rows = parse_daybook(xml)
    assert len(rows) == 1
    r = rows[0]
    assert r["vchtype"] == "Sales"
    assert r["vchnumber"] == "S-101"
    assert r["party"] == "Acme Distributors"
    assert r["amount"] == 1234.50
    # Verify customer details are extracted
    assert r["party_gstin"] == "27AABCU9603R1ZM"
    assert r["party_pincode"] == "400001"
    assert r["party_city"] == "Maharashtra"

def test_parse_daybook_without_customer_details():
    """Test that parser handles missing customer details gracefully"""
    xml = (Path(__file__).parent / "fixtures" / "daybook_sample.xml").read_text(encoding="utf-8")
    rows = parse_daybook(xml)
    assert len(rows) == 1
    r = rows[0]
    # When customer details are missing, should be None
    assert r["party_gstin"] is None
    assert r["party_pincode"] is None
    assert r["party_city"] is None

