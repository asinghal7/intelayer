"""Debug why run.py returns 0 records."""
from datetime import date, timedelta
import psycopg
from pathlib import Path
from adapters.tally_http.adapter import TallyHTTPAdapter
from agent.settings import TALLY_URL, TALLY_COMPANY, DB_URL
from agent.run import get_checkpoint

DAYBOOK_TEMPLATE = (Path(__file__).resolve().parents[1] / "adapters" / "tally_http" / "requests" / "daybook.xml.j2").read_text(encoding="utf-8")

with psycopg.connect(DB_URL) as conn:
    last = get_checkpoint(conn, "invoices")
    start = last - timedelta(days=1)
    end = date.today()
    
    print("=" * 80)
    print("RUN.PY DATE CALCULATION")
    print("=" * 80)
    print(f"Checkpoint (last): {last}")
    print(f"Start (last - 1):  {start}")
    print(f"End (today):       {end}")
    print(f"\nFetching from {start} to {end}")
    
    # Test what adapter returns
    print("\n" + "=" * 80)
    print("TESTING ADAPTER")
    print("=" * 80)
    
    adapter = TallyHTTPAdapter(TALLY_URL, TALLY_COMPANY, DAYBOOK_TEMPLATE, include_types=set())
    
    count = 0
    for inv in adapter.fetch_invoices(start, end):
        count += 1
        if count <= 3:
            print(f"\nInvoice {count}:")
            print(f"  Type: {inv.vchtype}")
            print(f"  Date: {inv.date}")
            print(f"  Customer: {inv.customer_id}")
            print(f"  Total: {inv.total}")
    
    print(f"\nTotal invoices returned by adapter: {count}")
    
    # Now test with today only
    print("\n" + "=" * 80)
    print("TESTING WITH TODAY ONLY")
    print("=" * 80)
    print(f"Fetching {date.today()}")
    
    count2 = 0
    for inv in adapter.fetch_invoices(date.today(), date.today()):
        count2 += 1
        if count2 <= 3:
            print(f"\nInvoice {count2}:")
            print(f"  Type: {inv.vchtype}")
            print(f"  Date: {inv.date}")
    
    print(f"\nTotal invoices for today: {count2}")
    
    # Test with Oct 11 (known good date)
    print("\n" + "=" * 80)
    print("TESTING WITH OCT 11 (KNOWN GOOD)")
    print("=" * 80)
    test_date = date(2025, 10, 11)
    print(f"Fetching {test_date}")
    
    count3 = 0
    for inv in adapter.fetch_invoices(test_date, test_date):
        count3 += 1
    
    print(f"\nTotal invoices for Oct 11: {count3} (expected: 9)")

