"""Reset checkpoint to test run.py."""
from datetime import date
import psycopg
from agent.settings import DB_URL

target_date = date(2025, 10, 10)

with psycopg.connect(DB_URL, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE etl_checkpoints 
            SET last_date = %s, updated_at = now()
            WHERE stream_name = 'invoices'
        """, (target_date,))
        
        cur.execute("SELECT last_date FROM etl_checkpoints WHERE stream_name = 'invoices'")
        new_date = cur.fetchone()[0]
        
        print(f"✓ Checkpoint reset to: {new_date}")
        print(f"  run.py will now fetch from {new_date} (with 1-day overlap)")

