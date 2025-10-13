from pathlib import Path
import pytest
from adapters.tally_http.parser import parse_daybook
from adapters.tally_http.validators import ensure_status_ok, TallyHTTPError

FIX = Path(__file__).parent / "fixtures"

def read(p): return (FIX / p).read_text(encoding="utf-8")

def test_status_ok_and_parse_daybook():
    xml = read("daybook_success.xml")
    ensure_status_ok(xml)  # no raise
    rows = parse_daybook(xml)
    assert len(rows) == 1
    r = rows[0]
    assert r["vchtype"] == "Sales"
    assert r["vchnumber"] == "S-101"
    assert r["party"] == "Acme Distributors"
    assert r["amount"] == 1234.50

def test_empty_ok():
    xml = read("daybook_empty.xml")
    ensure_status_ok(xml)  # status 1 but no DATA
    assert parse_daybook(xml) == []

def test_status_error_raises():
    xml = read("status_error.xml")
    with pytest.raises(TallyHTTPError):
        ensure_status_ok(xml)

