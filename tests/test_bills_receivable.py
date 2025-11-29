"""
Tests for bills receivable implementation.

Tests SQL structure, parser functionality, and loader logic.
"""
from pathlib import Path
from lxml import etree


def test_bills_receivable_migration_present():
    """Test that migration file exists and contains expected tables."""
    path = Path(__file__).resolve().parents[1] / "warehouse" / "migrations" / "0009_bills_receivable.sql"
    assert path.exists(), "Migration 0009_bills_receivable.sql must exist"
    sql = path.read_text()

    # Staging table
    assert "create table if not exists stg_trn_bill" in sql.lower()
    for fragment in [
        "voucher_guid text not null",
        "voucher_date date not null",
        "ledger text not null",
        "bill_name text not null",
        "amount numeric(14,2)",
        "billtype text",
    ]:
        assert fragment in sql.lower(), f"Expected column fragment missing in stg_trn_bill: {fragment}"

    # Fact table
    assert "create table if not exists fact_bills_receivable" in sql.lower()
    for fragment in [
        "ledger text not null",
        "bill_name text not null",
        "original_amount numeric(14,2)",
        "adjusted_amount numeric(14,2)",
        "pending_amount numeric(14,2)",
        "unique(ledger, bill_name)",
    ]:
        assert fragment in sql.lower(), f"Expected column fragment missing in fact_bills_receivable: {fragment}"

    # Indexes
    for idx in [
        "idx_stg_trn_bill_voucher_guid",
        "idx_stg_trn_bill_ledger",
        "idx_fact_bills_receivable_ledger",
        "idx_fact_bills_receivable_pending",
    ]:
        assert idx in sql, f"Expected index missing: {idx}"


def test_parse_trn_bill_allocations():
    """Test parser with sample XML containing bill allocations."""
    from adapters.tally_http.ar_ap.parser import parse_trn_bill_allocations
    
    # Sample XML with voucher and bill allocations
    xml = """<?xml version="1.0"?>
    <ENVELOPE>
        <BODY>
            <DATA>
                <VOUCHER>
                    <GUID>test-guid-123</GUID>
                    <DATE>01-Apr-2025</DATE>
                    <ALLLEDGERENTRIES.LIST>
                        <LEDGERNAME>Customer A</LEDGERNAME>
                        <BILLALLOCATIONS.LIST>
                            <NAME>INV-001</NAME>
                            <AMOUNT>10000.00</AMOUNT>
                            <BILLTYPE>New Ref</BILLTYPE>
                            <BILLCREDITPERIOD>30</BILLCREDITPERIOD>
                        </BILLALLOCATIONS.LIST>
                    </ALLLEDGERENTRIES.LIST>
                </VOUCHER>
            </DATA>
        </BODY>
    </ENVELOPE>
    """
    
    result = parse_trn_bill_allocations(xml)
    
    assert len(result) == 1
    row = result[0]
    assert row["voucher_guid"] == "test-guid-123"
    assert row["ledger"] == "Customer A"
    assert row["bill_name"] == "INV-001"
    assert row["amount"] == 10000.0
    assert row["billtype"] == "New Ref"
    assert row["bill_credit_period"] == 30


def test_parse_trn_bill_allocations_agst_ref():
    """Test parser handles 'Agst Ref' bill type (payments/adjustments)."""
    from adapters.tally_http.ar_ap.parser import parse_trn_bill_allocations
    
    xml = """<?xml version="1.0"?>
    <ENVELOPE>
        <BODY>
            <DATA>
                <VOUCHER>
                    <GUID>payment-guid-456</GUID>
                    <DATE>15-Apr-2025</DATE>
                    <ALLLEDGERENTRIES.LIST>
                        <LEDGERNAME>Customer A</LEDGERNAME>
                        <BILLALLOCATIONS.LIST>
                            <NAME>INV-001</NAME>
                            <AMOUNT>-5000.00</AMOUNT>
                            <BILLTYPE>Agst Ref</BILLTYPE>
                        </BILLALLOCATIONS.LIST>
                    </ALLLEDGERENTRIES.LIST>
                </VOUCHER>
            </DATA>
        </BODY>
    </ENVELOPE>
    """
    
    result = parse_trn_bill_allocations(xml)
    
    assert len(result) == 1
    row = result[0]
    assert row["billtype"] == "Agst Ref"
    assert row["amount"] == -5000.0  # Negative for payment

