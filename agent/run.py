from datetime import date, timedelta
import psycopg
from loguru import logger
from pathlib import Path
from adapters.tally_http.adapter import TallyHTTPAdapter
from agent.settings import TALLY_URL, TALLY_COMPANY, DB_URL

DAYBOOK_TEMPLATE = (Path(__file__).resolve().parents[1] / "adapters" / "tally_http" / "requests" / "daybook.xml.j2").read_text(encoding="utf-8")

def get_checkpoint(conn, stream: str) -> date:
    with conn.cursor() as cur:
        cur.execute("select last_date from etl_checkpoints where stream_name=%s", (stream,))
        row = cur.fetchone()
        fy_start = date(date.today().year if date.today().month>=4 else date.today().year-1, 4, 1)
        return row[0] if row and row[0] else fy_start

def upsert_customer(conn, customer_id: str):
    """Ensure customer exists in dim_customer before inserting invoice."""
    with conn.cursor() as cur:
        cur.execute("""
          insert into dim_customer (customer_id, name)
          values (%s, %s)
          on conflict (customer_id) do nothing
        """, (customer_id, customer_id))

def upsert_invoice(conn, inv):
    # First ensure the customer exists
    upsert_customer(conn, inv.customer_id)
    
    with conn.cursor() as cur:
        cur.execute("""
          insert into fact_invoice (invoice_id, voucher_key, vchtype, date, customer_id, sp_id, subtotal, tax, total, roundoff)
          values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
          on conflict (invoice_id) do update set
            vchtype=excluded.vchtype,
            date=excluded.date,
            customer_id=excluded.customer_id,
            subtotal=excluded.subtotal,
            tax=excluded.tax,
            total=excluded.total,
            roundoff=excluded.roundoff
        """, (
            inv.invoice_id, inv.voucher_key, inv.vchtype, inv.date, inv.customer_id, inv.sp_id,
            inv.subtotal, inv.tax, inv.total, inv.roundoff
        ))

def log_run(conn, rows: int, status: str, err: str | None = None):
    with conn.cursor() as cur:
        cur.execute("insert into etl_logs(stream_name, rows, status, error) values(%s,%s,%s,%s)",
                    ("invoices", rows, status, err))

def main():
    # Pass empty set to include ALL voucher types (Sales, Receipt, Payment, Journal, etc.)
    adapter = TallyHTTPAdapter(TALLY_URL, TALLY_COMPANY, DAYBOOK_TEMPLATE, include_types=set())
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        try:
            last = get_checkpoint(conn, "invoices")
            start = last - timedelta(days=1)  # overlap for late edits
            end = date.today()
            count = 0
            for inv in adapter.fetch_invoices(start, end):
                upsert_invoice(conn, inv); count += 1
            with conn.cursor() as cur:
                cur.execute("""
                  insert into etl_checkpoints(stream_name,last_date) values('invoices', %s)
                  on conflict(stream_name) do update set last_date=excluded.last_date, updated_at=now()
                """, (end,))
            log_run(conn, count, "ok")
            logger.info(f"Invoices upserted: {count}")
        except Exception as e:
            log_run(conn, 0, "error", str(e))
            raise

if __name__ == "__main__":
    main()

