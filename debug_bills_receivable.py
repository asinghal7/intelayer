"""
Debug script to check bills receivable calculation.
"""
import psycopg
from agent.settings import DB_URL

with psycopg.connect(DB_URL, autocommit=True) as conn:
    with conn.cursor() as cur:
        # Check a specific bill to see if amounts match
        print("=== Sample Bill Analysis ===\n")
        
        # Find a bill with both New Ref and Agst Ref
        cur.execute("""
            select 
                ledger, 
                bill_name,
                sum(case when billtype = 'New Ref' or billtype is null or billtype = '' then abs(amount) else 0 end) as new_ref_total,
                sum(case when billtype = 'Agst Ref' then abs(amount) else 0 end) as agst_ref_total,
                count(*) as transaction_count
            from stg_trn_bill
            group by ledger, bill_name
            having sum(case when billtype = 'New Ref' or billtype is null or billtype = '' then abs(amount) else 0 end) > 0
               and sum(case when billtype = 'Agst Ref' then abs(amount) else 0 end) > 0
            limit 5
        """)
        
        print("Bills with both New Ref and Agst Ref:")
        for row in cur.fetchall():
            ledger, bill_name, new_ref, agst_ref, count = row
            expected_pending = new_ref - agst_ref
            print(f"  {ledger} / {bill_name}:")
            print(f"    New Ref total: {new_ref}")
            print(f"    Agst Ref total: {agst_ref}")
            print(f"    Expected pending: {expected_pending}")
            
            # Check fact table
            cur.execute("""
                select original_amount, adjusted_amount, pending_amount
                from fact_bills_receivable
                where ledger = %s and bill_name = %s
            """, (ledger, bill_name))
            fact_row = cur.fetchone()
            if fact_row:
                orig, adj, pending = fact_row
                print(f"    Fact table: orig={orig}, adj={adj}, pending={pending}")
                if abs(pending - expected_pending) > 0.01:
                    print(f"    ⚠️  MISMATCH! Expected {expected_pending}, got {pending}")
            else:
                print(f"    ⚠️  Not found in fact table!")
            print()
        
        # Check opening balances
        print("\n=== Opening Balances ===")
        cur.execute("""
            select ledger, name, opening_balance
            from mst_opening_bill_allocation
            where opening_balance != 0
            limit 5
        """)
        for row in cur.fetchall():
            print(f"  {row[0]} / {row[1]}: {row[2]}")
        
        # Summary stats
        print("\n=== Summary ===")
        cur.execute("select count(*), sum(pending_amount) from fact_bills_receivable")
        count, total = cur.fetchone()
        print(f"Total bills in fact table: {count}")
        print(f"Total pending amount: {total}")



