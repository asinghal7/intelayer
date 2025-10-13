from pathlib import Path
from adapters.tally_http.parser import parse_daybook

def test_repeated_customer_multiple_vouchers():
    """Test that multiple vouchers for the same customer are all parsed correctly."""
    xml = (Path(__file__).parent / "fixtures" / "daybook_repeated_customer.xml").read_text(encoding="utf-8")
    rows = parse_daybook(xml)
    
    # Should have 3 vouchers
    assert len(rows) == 3, f"Expected 3 vouchers, got {len(rows)}"
    
    # All should be for the same customer
    assert all(r["party"] == "Acme Distributors" for r in rows)
    
    # Check first voucher
    assert rows[0]["vchnumber"] == "S-101"
    assert rows[0]["amount"] == 1000.00
    assert rows[0]["guid"] == "guid-101"
    
    # Check second voucher
    assert rows[1]["vchnumber"] == "S-102"
    assert rows[1]["amount"] == 2000.00
    assert rows[1]["guid"] == "guid-102"
    
    # Check third voucher
    assert rows[2]["vchnumber"] == "S-103"
    assert rows[2]["amount"] == 3000.00
    assert rows[2]["guid"] == "guid-103"

