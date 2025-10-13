"""Test that duplicate keys are handled correctly."""
from adapters.tally_http.adapter import _voucher_key

def test_duplicate_keys_with_empty_vchnumber():
    """Test that vouchers without vchnumber but same party/date don't collide."""
    
    # Two invoices for same customer on same date, no vchnumber, no GUID
    voucher1 = {
        "vchtype": "Invoice",
        "vchnumber": "",  # Empty!
        "date": "2025-10-13",
        "party": "Khanna Radios",
        "guid": "",  # Empty!
        "amount": 10000.00
    }
    
    voucher2 = {
        "vchtype": "Invoice",  # Same type
        "vchnumber": "",  # Empty!
        "date": "2025-10-13",  # Same date
        "party": "Khanna Radios",  # Same party
        "guid": "",  # Empty!
        "amount": 20000.00  # Different amount
    }
    
    key1 = _voucher_key(voucher1)
    key2 = _voucher_key(voucher2)
    
    print(f"Key 1: {key1}")
    print(f"Key 2: {key2}")
    
    # Keys should be unique because amounts are different
    assert key1 != key2, f"Keys should be unique but both are: {key1}"
    
    # Keys should contain hash suffix
    assert '#' in key1, "Key should contain hash suffix when GUID and vchnumber are empty"
    assert '#' in key2, "Key should contain hash suffix when GUID and vchnumber are empty"


def test_guid_priority():
    """Test that GUID is used when available."""
    voucher = {
        "vchtype": "Sales",
        "vchnumber": "S-101",
        "date": "2025-10-13",
        "party": "Test Customer",
        "guid": "abcd-1234-5678",
        "amount": 1000.00
    }
    
    key = _voucher_key(voucher)
    assert key == "abcd-1234-5678", "GUID should be used as key when available"


def test_vchnumber_priority():
    """Test that vchnumber format is used when GUID is empty."""
    voucher = {
        "vchtype": "Sales",
        "vchnumber": "S-101",
        "date": "2025-10-13",
        "party": "Test Customer",
        "guid": "",
        "amount": 1000.00
    }
    
    key = _voucher_key(voucher)
    assert key == "Sales/S-101/2025-10-13/Test Customer", "Should use vchnumber format when GUID is empty"
    assert '#' not in key, "Should not use hash when vchnumber is available"

