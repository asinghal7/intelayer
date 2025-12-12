"""
Tests for XML parsers.

Tests parsing of various Tally XML formats.
"""
import pytest
from datetime import date
from tally_db_loader.parsers.base import (
    sanitize_xml,
    parse_tally_date,
    parse_float,
    parse_bool,
    parse_int,
)
from tally_db_loader.parsers.masters import (
    parse_groups,
    parse_ledgers,
    parse_stock_items,
)
from tally_db_loader.parsers.transactions import parse_vouchers


class TestBaseParsers:
    """Tests for base parsing utilities."""
    
    def test_sanitize_xml_removes_control_chars(self):
        """Test that control characters are removed."""
        xml = "test\x00\x01\x02value"
        result = sanitize_xml(xml)
        assert "\x00" not in result
        assert "test" in result
        assert "value" in result
    
    def test_sanitize_xml_fixes_ampersands(self):
        """Test that unescaped ampersands are fixed."""
        xml = "<name>A & B</name>"
        result = sanitize_xml(xml)
        assert "&amp;" in result
    
    def test_parse_tally_date_yyyymmdd(self):
        """Test parsing YYYYMMDD format."""
        result = parse_tally_date("20240401")
        assert result == date(2024, 4, 1)
    
    def test_parse_tally_date_iso(self):
        """Test parsing ISO format."""
        result = parse_tally_date("2024-04-01")
        assert result == date(2024, 4, 1)
    
    def test_parse_tally_date_dmy(self):
        """Test parsing DD-MMM-YYYY format."""
        result = parse_tally_date("01-Apr-2024")
        assert result == date(2024, 4, 1)
    
    def test_parse_tally_date_empty(self):
        """Test parsing empty date."""
        assert parse_tally_date("") is None
        assert parse_tally_date(None) is None
    
    def test_parse_float_simple(self):
        """Test parsing simple float."""
        assert parse_float("123.45") == 123.45
    
    def test_parse_float_with_commas(self):
        """Test parsing float with comma separators."""
        assert parse_float("1,234.56") == 1234.56
    
    def test_parse_float_parentheses_negative(self):
        """Test parsing negative in parentheses."""
        assert parse_float("(123.45)") == -123.45
    
    def test_parse_float_empty(self):
        """Test parsing empty returns default."""
        assert parse_float("") == 0.0
        assert parse_float("", default=100) == 100
    
    def test_parse_bool_yes(self):
        """Test parsing Yes as True."""
        assert parse_bool("Yes") is True
        assert parse_bool("yes") is True
        assert parse_bool("YES") is True
    
    def test_parse_bool_no(self):
        """Test parsing No as False."""
        assert parse_bool("No") is False
        assert parse_bool("no") is False
    
    def test_parse_bool_numeric(self):
        """Test parsing numeric booleans."""
        assert parse_bool("1") is True
        assert parse_bool("0") is False
    
    def test_parse_int_simple(self):
        """Test parsing simple integer."""
        assert parse_int("123") == 123
    
    def test_parse_int_with_decimal(self):
        """Test parsing integer from decimal string."""
        assert parse_int("123.0") == 123


class TestMasterParsers:
    """Tests for master data parsers."""
    
    SAMPLE_GROUP_XML = """
    <ENVELOPE>
        <BODY>
            <DATA>
                <COLLECTION>
                    <GROUP NAME="Sundry Debtors" GUID="abc123">
                        <ALTERID>1</ALTERID>
                        <PARENT>Current Assets</PARENT>
                        <ISREVENUE>No</ISREVENUE>
                        <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                    </GROUP>
                </COLLECTION>
            </DATA>
        </BODY>
    </ENVELOPE>
    """
    
    SAMPLE_LEDGER_XML = """
    <ENVELOPE>
        <BODY>
            <DATA>
                <COLLECTION>
                    <LEDGER NAME="ABC Corp" GUID="led123">
                        <ALTERID>100</ALTERID>
                        <PARENT>Sundry Debtors</PARENT>
                        <OPENINGBALANCE>50000</OPENINGBALANCE>
                        <GSTIN>29ABCDE1234F1Z5</GSTIN>
                        <ISBILLWISEON>Yes</ISBILLWISEON>
                        <LEDGERBILLALLOCATIONS.LIST>
                            <NAME>INV001</NAME>
                            <OPENINGBALANCE>10000</OPENINGBALANCE>
                            <BILLDATE>20240101</BILLDATE>
                        </LEDGERBILLALLOCATIONS.LIST>
                    </LEDGER>
                </COLLECTION>
            </DATA>
        </BODY>
    </ENVELOPE>
    """
    
    def test_parse_groups(self):
        """Test parsing ledger groups."""
        groups = parse_groups(self.SAMPLE_GROUP_XML)
        assert len(groups) == 1
        
        group = groups[0]
        assert group["name"] == "Sundry Debtors"
        assert group["guid"] == "abc123"
        assert group["parent"] == "Current Assets"
        assert group["is_revenue"] is False
        assert group["is_deemed_positive"] is True
    
    def test_parse_ledgers(self):
        """Test parsing ledgers with opening bills."""
        ledgers, opening_bills = parse_ledgers(self.SAMPLE_LEDGER_XML)
        
        assert len(ledgers) == 1
        ledger = ledgers[0]
        assert ledger["name"] == "ABC Corp"
        assert ledger["guid"] == "led123"
        assert ledger["parent"] == "Sundry Debtors"
        assert ledger["opening_balance"] == 50000
        assert ledger["gstin"] == "29ABCDE1234F1Z5"
        assert ledger["is_bill_wise_on"] is True
        
        assert len(opening_bills) == 1
        bill = opening_bills[0]
        assert bill["ledger"] == "ABC Corp"
        assert bill["name"] == "INV001"
        assert bill["opening_balance"] == 10000


class TestTransactionParsers:
    """Tests for transaction parsers."""
    
    SAMPLE_VOUCHER_XML = """
    <ENVELOPE>
        <BODY>
            <DATA>
                <TALLYMESSAGE>
                    <VOUCHER VCHTYPE="Sales" VCHNUMBER="001" GUID="vch123">
                        <DATE>20240415</DATE>
                        <PARTYLEDGERNAME>ABC Corp</PARTYLEDGERNAME>
                        <NARRATION>April sale</NARRATION>
                        <ISINVOICE>Yes</ISINVOICE>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>ABC Corp</LEDGERNAME>
                            <AMOUNT>-11800</AMOUNT>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Sales @ 18%</LEDGERNAME>
                            <AMOUNT>10000</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>CGST</LEDGERNAME>
                            <AMOUNT>900</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>SGST</LEDGERNAME>
                            <AMOUNT>900</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLINVENTORYENTRIES.LIST>
                            <STOCKITEMNAME>Product A</STOCKITEMNAME>
                            <BILLEDQTY>10 Nos</BILLEDQTY>
                            <RATE>1000</RATE>
                            <AMOUNT>-10000</AMOUNT>
                        </ALLINVENTORYENTRIES.LIST>
                        <BILLALLOCATIONS.LIST>
                            <NAME>INV-2024-001</NAME>
                            <BILLTYPE>New Ref</BILLTYPE>
                            <AMOUNT>-11800</AMOUNT>
                        </BILLALLOCATIONS.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </DATA>
        </BODY>
    </ENVELOPE>
    """
    
    def test_parse_vouchers(self):
        """Test parsing vouchers with all related entries."""
        result = parse_vouchers(self.SAMPLE_VOUCHER_XML)
        
        # Check voucher header
        assert len(result["vouchers"]) == 1
        voucher = result["vouchers"][0]
        assert voucher["guid"] == "vch123"
        assert voucher["voucher_type"] == "Sales"
        assert voucher["voucher_number"] == "001"
        assert voucher["party_name"] == "ABC Corp"
        assert voucher["is_invoice"] is True
        assert voucher["date"] == date(2024, 4, 15)
        
        # Check accounting entries
        assert len(result["accounting"]) == 4
        party_entry = next(e for e in result["accounting"] if e["is_party_ledger"])
        assert party_entry["ledger"] == "ABC Corp"
        assert party_entry["amount"] == -11800
        # Verify debit/credit calculation (negative amount = debit)
        assert party_entry["amount_debit"] == 11800  # abs(-11800)
        assert party_entry["amount_credit"] == 0
        
        # Check a credit entry (Sales @ 18%)
        sales_entry = next(e for e in result["accounting"] if e["ledger"] == "Sales @ 18%")
        assert sales_entry["amount"] == 10000  # positive = credit
        assert sales_entry["amount_debit"] == 0
        assert sales_entry["amount_credit"] == 10000
        
        # Check inventory entries
        assert len(result["inventory"]) == 1
        inv = result["inventory"][0]
        assert inv["stock_item"] == "Product A"
        assert inv["billed_qty"] == 10
        assert inv["rate"] == 1000
        
        # Check bill allocations
        assert len(result["bills"]) == 1
        bill = result["bills"][0]
        assert bill["name"] == "INV-2024-001"
        assert bill["bill_type"] == "New Ref"
        assert bill["amount"] == -11800


# Run tests directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

