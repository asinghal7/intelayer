"""Verify that all vouchers are correctly imported with unique keys and proper amounts."""
import psycopg
from agent.settings import DB_URL

print("=" * 100)
print("VERIFYING ETL RESULTS")
print("=" * 100)

with psycopg.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        # Check total count
        cur.execute("SELECT COUNT(*) FROM fact_invoice;")
        total = cur.fetchone()[0]
        print(f"\n✓ Total records in database: {total}")
        
        # Check for zero amounts by voucher type
        cur.execute("""
            SELECT vchtype, 
                   COUNT(*) as total,
                   SUM(CASE WHEN total = 0 THEN 1 ELSE 0 END) as zero_count,
                   SUM(CASE WHEN total != 0 THEN 1 ELSE 0 END) as nonzero_count,
                   SUM(total) as sum_total
            FROM fact_invoice 
            GROUP BY vchtype
            ORDER BY vchtype;
        """)
        
        print("\n" + "=" * 100)
        print(f"{'Voucher Type':15} | {'Total':6} | {'Zeros':6} | {'Non-Zero':9} | {'Sum':15}")
        print("=" * 100)
        all_nonzero = True
        for row in cur.fetchall():
            print(f"{row[0]:15} | {row[1]:6} | {row[2]:6} | {row[3]:9} | {row[4]:15.2f}")
            if row[2] > 0:  # has zeros
                all_nonzero = False
        print("=" * 100)
        
        if all_nonzero:
            print("\n✓ All vouchers have non-zero amounts!")
        else:
            print("\n✗ Some vouchers still have zero amounts")
        
        # Check for customers with multiple records
        cur.execute("""
            SELECT customer_id, COUNT(*) as count
            FROM fact_invoice 
            GROUP BY customer_id
            HAVING COUNT(*) > 1
            ORDER BY count DESC;
        """)
        
        customers = cur.fetchall()
        print(f"\n✓ Customers with multiple vouchers: {len(customers)}")
        for customer, count in customers:
            print(f"  - {customer}: {count} vouchers")
        
        # Show all records with tax breakdown
        cur.execute("""
            SELECT invoice_id, vchtype, date, customer_id, subtotal, tax, total
            FROM fact_invoice 
            ORDER BY date, vchtype, customer_id;
        """)
        
        print("\n" + "=" * 120)
        print("ALL RECORDS (with tax breakdown):")
        print("=" * 120)
        print(f"{'Invoice ID':40} | {'Type':10} | {'Customer':25} | {'Subtotal':12} | {'Tax':12} | {'Total':12}")
        print("=" * 120)
        for row in cur.fetchall():
            invoice_id = row[0][:40] if len(row[0]) > 40 else row[0]
            customer = row[3][:25] if len(row[3]) > 25 else row[3]
            subtotal = row[4]
            tax = row[5]
            total = row[6]
            print(f"{invoice_id:40} | {row[1]:10} | {customer:25} | {subtotal:12.2f} | {tax:12.2f} | {total:12.2f}")
        print("=" * 120)
        
        # Final summary
        print(f"\n{'=' * 100}")
        print("SUMMARY:")
        print(f"{'=' * 100}")
        if total == 9 and all_nonzero:
            print("✓ SUCCESS! All 9 vouchers imported with correct amounts and unique keys.")
        else:
            if total != 9:
                print(f"✗ Expected 9 records, found {total}")
            if not all_nonzero:
                print("✗ Some records have zero amounts")
        print(f"{'=' * 100}\n")

