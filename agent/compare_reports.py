"""Compare DayBook vs Voucher Register data for Oct 11."""
from datetime import date
from adapters.tally_http.client import TallyClient
from adapters.tally_http.parser import parse_daybook
from agent.settings import TALLY_URL, TALLY_COMPANY
import json

client = TallyClient(TALLY_URL, TALLY_COMPANY)

test_date = date(2025, 10, 11)
test_date_str = test_date.strftime("%d-%b-%Y")

# Test DayBook
xml_daybook = f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>DayBook</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVFROMDATE TYPE="Date">{test_date_str}</SVFROMDATE>
        <SVTODATE TYPE="Date">{test_date_str}</SVTODATE>
        <SVCurrentCompany>{TALLY_COMPANY}</SVCurrentCompany>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""

# Test Voucher Register
xml_voucher = f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Voucher Register</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVFROMDATE TYPE="Date">{test_date_str}</SVFROMDATE>
        <SVTODATE TYPE="Date">{test_date_str}</SVTODATE>
        <SVCurrentCompany>{TALLY_COMPANY}</SVCurrentCompany>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""

print("=" * 80)
print(f"COMPARING DAYBOOK VS VOUCHER REGISTER FOR {test_date}")
print("=" * 80)

response_daybook = client.post_xml(xml_daybook)
vouchers_daybook = parse_daybook(response_daybook)

response_voucher = client.post_xml(xml_voucher)
vouchers_voucher = parse_daybook(response_voucher)

print(f"\nDayBook: {len(vouchers_daybook)} vouchers")
print(f"Voucher Register: {len(vouchers_voucher)} vouchers")

# Compare first voucher structure
if vouchers_daybook and vouchers_voucher:
    print("\n" + "=" * 80)
    print("FIRST VOUCHER COMPARISON")
    print("=" * 80)
    
    print("\nDayBook first voucher:")
    for key, val in vouchers_daybook[0].items():
        print(f"  {key}: {val}")
    
    print("\nVoucher Register first voucher:")
    for key, val in vouchers_voucher[0].items():
        print(f"  {key}: {val}")
    
    # Check if keys match
    daybook_keys = set(vouchers_daybook[0].keys())
    voucher_keys = set(vouchers_voucher[0].keys())
    
    print("\n" + "=" * 80)
    print("KEY COMPARISON")
    print("=" * 80)
    print(f"Keys match: {daybook_keys == voucher_keys}")
    
    if daybook_keys != voucher_keys:
        print(f"Only in DayBook: {daybook_keys - voucher_keys}")
        print(f"Only in Voucher Register: {voucher_keys - daybook_keys}")
    
    # Compare all vouchers
    print("\n" + "=" * 80)
    print("ALL VOUCHERS")
    print("=" * 80)
    
    print("\nDayBook vouchers (type, date, party, total):")
    for i, v in enumerate(vouchers_daybook[:10], 1):
        print(f"  {i}. {v['vchtype']:15s} {v['date']} {v['party'][:25]:25s} {v['total']:10.2f}")
    
    print(f"\nVoucher Register vouchers (type, date, party, total):")
    for i, v in enumerate(vouchers_voucher[:10], 1):
        print(f"  {i}. {v['vchtype']:15s} {v['date']} {v['party'][:25]:25s} {v['total']:10.2f}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("If data structures and values match, Voucher Register is a safe replacement.")

