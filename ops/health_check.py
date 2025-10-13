import os, psycopg, sys
from datetime import timedelta, datetime, timezone

DB_URL = os.getenv("DB_URL", "postgresql://inteluser:change_me@localhost:5432/intelayer")
MAX_AGE_MIN = int(os.getenv("MAX_AGE_MIN", "180"))

with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
    cur.execute("select max(run_at) from etl_logs where stream_name='invoices' and status='ok'")
    row = cur.fetchone()
    last = row[0]
    if not last or (datetime.now(timezone.utc) - last) > timedelta(minutes=MAX_AGE_MIN):
        print("ETL stale or missing"); sys.exit(1)
print("ETL healthy")

