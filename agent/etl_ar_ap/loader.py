from __future__ import annotations
from datetime import date, timedelta
from time import sleep
from loguru import logger
import psycopg
from adapters.tally_http.ar_ap.adapter import TallyARAPAdapter
from adapters.tally_http.ar_ap.parser import (
    parse_opening_bill_allocations,
    parse_trn_bill_allocations,
    parse_outstanding_receivables,
)


def upsert_opening_bills(conn, rows: list[dict]) -> int:
    if not rows:
        return 0
    inserted = 0
    with conn.cursor() as cur:
        for r in rows:
            cur.execute(
                """
                insert into mst_opening_bill_allocation (
                  ledger, name, bill_date, opening_balance, bill_credit_period, is_advance
                ) values (%s,%s,%s,%s,%s,%s)
                on conflict do nothing
                """,
                (
                    r.get("ledger"),
                    r.get("name"),
                    r.get("bill_date"),
                    r.get("opening_balance", 0.0),
                    r.get("bill_credit_period"),
                    r.get("is_advance", False),
                ),
            )
            inserted += 1
    return inserted


def run_mst_opening_bill_allocation_pipeline(db_url: str, tally_url: str, tally_company: str) -> int:
    """
    Minimal pipeline to populate mst_opening_bill_allocation from Tally masters.
    """
    adapter = TallyARAPAdapter(tally_url, tally_company)
    xml = adapter.fetch_ledgers_with_opening_bills_xml()
    rows = parse_opening_bill_allocations(xml)
    logger.info(f"Parsed opening bill allocations: {len(rows)}")
    with psycopg.connect(db_url, autocommit=True) as conn:
        count = upsert_opening_bills(conn, rows)
        logger.info(f"Inserted opening bill allocations: {count}")
        return count


def load_stg_trn_bill(conn, rows: list[dict]) -> int:
    """
    Load transaction bill allocations into staging table.
    Truncates staging table before inserting new data.
    """
    if not rows:
        return 0
    
    with conn.cursor() as cur:
        # Truncate staging table
        cur.execute("truncate table stg_trn_bill")
        
        # Insert all rows
        inserted = 0
        for r in rows:
            cur.execute(
                """
                insert into stg_trn_bill (
                  voucher_guid, voucher_date, ledger, bill_name, amount, billtype, bill_credit_period
                ) values (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    r.get("voucher_guid"),
                    r.get("voucher_date"),
                    r.get("ledger"),
                    r.get("bill_name"),
                    r.get("amount", 0.0),
                    r.get("billtype"),
                    r.get("bill_credit_period"),
                ),
            )
            inserted += 1
    
    return inserted


def load_tally_loader_trn_tables(conn, rows: list[dict]) -> tuple[int, int]:
    """
    Populate tally_loader.trn_voucher and tally_loader.trn_bill tables.
    Returns a tuple of (voucher_rows, bill_rows) inserted.
    """
    if not rows:
        return 0, 0
    
    vouchers: dict[str, dict] = {}
    bill_rows: list[tuple] = []
    
    for r in rows:
        guid = r.get("voucher_guid")
        if not guid:
            continue
        
        # Collect voucher-level data once per GUID
        if guid not in vouchers:
            vouchers[guid] = {
                "guid": guid,
                "alterid": r.get("alter_id"),
                "date": r.get("voucher_date"),
                "voucher_type": r.get("voucher_type"),
                "voucher_number": r.get("voucher_number"),
                "reference_number": r.get("reference_number"),
                "reference_date": r.get("reference_date"),
                "narration": r.get("narration"),
                "party_name": r.get("party_name"),
                "place_of_supply": r.get("place_of_supply"),
                "is_invoice": bool(r.get("is_invoice")),
                "is_accounting_voucher": bool(r.get("is_accounting_voucher")),
                "is_inventory_voucher": bool(r.get("is_inventory_voucher")),
                "is_order_voucher": bool(r.get("is_order_voucher")),
            }
        
        bill_rows.append(
            (
                guid,
                r.get("ledger"),
                (r.get("ledger") or "").lower() or None,
                r.get("bill_name"),
                r.get("amount", 0.0),
                r.get("billtype") or "",
                r.get("bill_credit_period"),
            )
        )
    
    with conn.cursor() as cur:
        voucher_values = [
            (
                v["guid"],
                v["alterid"],
                v["date"],
                v["voucher_type"],
                (v["voucher_type"] or "").lower() or None,
                v["voucher_number"],
                v["reference_number"],
                v["reference_date"],
                v["narration"],
                v["party_name"],
                (v["party_name"] or "").lower() or None,
                v["place_of_supply"],
                v["is_invoice"],
                v["is_accounting_voucher"],
                v["is_inventory_voucher"],
                v["is_order_voucher"],
            )
            for v in vouchers.values()
        ]
        
        if voucher_values:
            cur.executemany(
                """
                insert into tally_loader.trn_voucher (
                    guid, alterid, date, voucher_type, voucher_type_internal, voucher_number,
                    reference_number, reference_date, narration, party_name, party_name_internal,
                    place_of_supply, is_invoice, is_accounting_voucher, is_inventory_voucher, is_order_voucher
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                voucher_values,
            )
        
        if bill_rows:
            cur.executemany(
                """
                insert into tally_loader.trn_bill (
                    guid, ledger, ledger_internal, name, amount, billtype, bill_credit_period
                ) values (%s,%s,%s,%s,%s,%s,%s)
                """,
                bill_rows,
            )
    
    return len(voucher_values), len(bill_rows)


def upsert_fact_bills_receivable_from_outstanding(conn, rows: list[dict]) -> int:
    """
    Upsert fact_bills_receivable directly from Outstanding Receivables report.
    
    This is more accurate than reconstructing from transactions because Tally
    provides the correct pending amounts directly, including bills created before
    our date range.
    
    Args:
        conn: Database connection
        rows: List of dicts from parse_outstanding_receivables
    
    Returns:
        Number of rows upserted
    """
    if not rows:
        return 0
    
    with conn.cursor() as cur:
        inserted = 0
        for r in rows:
            # Calculate adjusted_amount from original and pending
            original = r.get("original_amount", 0.0)
            pending = r.get("pending_amount", 0.0)
            adjusted = original - pending
            
            cur.execute(
                """
                insert into fact_bills_receivable (
                    ledger, bill_name, bill_date, due_date, original_amount, adjusted_amount,
                    pending_amount, billtype, is_advance, last_adjusted_date, last_seen_at
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                on conflict (ledger, bill_name) do update set
                    bill_date = excluded.bill_date,
                    due_date = excluded.due_date,
                    original_amount = excluded.original_amount,
                    adjusted_amount = excluded.adjusted_amount,
                    pending_amount = excluded.pending_amount,
                    billtype = excluded.billtype,
                    is_advance = excluded.is_advance,
                    last_adjusted_date = excluded.last_adjusted_date,
                    last_seen_at = now()
                """,
                (
                    r.get("ledger"),
                    r.get("bill_name"),
                    r.get("bill_date"),
                    r.get("due_date"),
                    original,
                    adjusted,
                    pending,
                    r.get("billtype", "Outstanding"),
                    r.get("is_advance", False),
                    None,  # last_adjusted_date not available from outstanding report
                ),
            )
            inserted += 1
        
        return inserted


def upsert_fact_bills_receivable(conn) -> int:
    """
    Recompute fact_bills_receivable using open-source Tally loader logic.
    Relies on tally_loader.trn_voucher, tally_loader.trn_bill, and the view
    tally_loader.mst_opening_bill_allocation.
    """
    with conn.cursor() as cur:
        cur.execute("""
            with bill_combined as (
                select
                    bill_date as date,
                    ledger,
                    name,
                    opening_balance as amount,
                    'New Ref'::text as billtype,
                    bill_credit_period,
                    (is_advance = 1) as is_advance
                from tally_loader.mst_opening_bill_allocation
                where coalesce(name, '') <> ''
                  and opening_balance is not null
                  and opening_balance <> 0
                union all
                select
                    v.date,
                    b.ledger,
                    b.name,
                    b.amount,
                    coalesce(nullif(b.billtype, ''), 'New Ref') as billtype,
                    coalesce(b.bill_credit_period, 0) as bill_credit_period,
                    false as is_advance
                from tally_loader.trn_bill b
                join tally_loader.trn_voucher v on v.guid = b.guid
                where coalesce(b.name, '') <> ''
            ),
            tbl_newref as (
                select *
                from bill_combined
                where billtype in ('New Ref', 'Advance', 'Opening')
            ),
            tbl_agstref as (
                select *
                from bill_combined
                where billtype in ('Agst Ref')
            ),
            tbl_outstanding as (
                select
                    nr.ledger,
                    nr.name,
                    coalesce(max(nr.date), max(ar.date)) as bill_date,
                    coalesce(max(nr.bill_credit_period), 0) as bill_credit_period,
                    bool_or(nr.is_advance) as is_advance,
                    case
                        when bool_or(nr.billtype = 'Opening') then 'Opening'
                        else 'New Ref'
                    end as billtype,
                    coalesce(sum(nr.amount), 0) as billed_raw,
                    coalesce(sum(ar.amount), 0) as adjusted_raw,
                    max(ar.date) as last_adjusted_date
                from tbl_newref nr
                left join tbl_agstref ar
                    on nr.ledger = ar.ledger
                   and nr.name = ar.name
                group by nr.ledger, nr.name
            )
            insert into fact_bills_receivable (
                ledger,
                bill_name,
                bill_date,
                due_date,
                original_amount,
                adjusted_amount,
                pending_amount,
                billtype,
                is_advance,
                last_adjusted_date,
                last_seen_at
            )
            select
                ledger,
                name as bill_name,
                bill_date,
                case
                    when bill_date is not null and bill_credit_period > 0
                        then (bill_date + (bill_credit_period || ' days')::interval)::date
                    else null
                end as due_date,
                abs(billed_raw) as original_amount,
                abs(adjusted_raw) as adjusted_amount,
                abs(billed_raw + adjusted_raw) as pending_amount,
                billtype,
                is_advance,
                last_adjusted_date,
                now()
            from tbl_outstanding
            where (billed_raw + adjusted_raw) < 0
            on conflict (ledger, bill_name) do update set
                bill_date = excluded.bill_date,
                due_date = excluded.due_date,
                original_amount = excluded.original_amount,
                adjusted_amount = excluded.adjusted_amount,
                pending_amount = excluded.pending_amount,
                billtype = excluded.billtype,
                is_advance = excluded.is_advance,
                last_adjusted_date = excluded.last_adjusted_date,
                last_seen_at = now()
        """)
        
        rows_affected = cur.rowcount
        return rows_affected


def run_bills_receivable_pipeline(
    db_url: str,
    tally_url: str,
    tally_company: str,
    from_date: date,
    to_date: date,
    batch_days: int = 30,
    reset_fact: bool = True,
) -> int:
    """
    Complete pipeline to populate bills receivable fact table.
    
    Processes data in batches to avoid overwhelming Tally with large date ranges.
    
    Steps:
    1. Fetch vouchers with bill allocations from Tally (in batches)
    2. Parse and accumulate bill allocations
    3. Load into staging table
    4. Transform and upsert into fact table
    
    Args:
        batch_days: Number of days per batch (default 30 to avoid timeouts)
    """
    adapter = TallyARAPAdapter(tally_url, tally_company)
    
    # Process in batches to avoid Tally crashes
    all_rows: list[dict] = []
    current_date = from_date
    
    logger.info(f"Processing bills receivable from {from_date} to {to_date} in {batch_days}-day batches")
    
    while current_date <= to_date:
        batch_end = min(current_date + timedelta(days=batch_days - 1), to_date)
        logger.info(f"Fetching batch: {current_date} to {batch_end}")
        
        try:
            xml = adapter.fetch_vouchers_with_bills_xml(current_date, batch_end)
            batch_rows = parse_trn_bill_allocations(xml)
            all_rows.extend(batch_rows)
            logger.info(f"  Parsed {len(batch_rows)} bill allocation rows (total: {len(all_rows)})")
        except Exception as e:
            logger.error(f"  Error processing batch {current_date} to {batch_end}: {e}")
            raise
        
        # Small delay between batches to give Tally time to recover
        if current_date + timedelta(days=batch_days) <= to_date:
            sleep(1)  # 1 second delay between batches
        
        # Move to next batch
        current_date = batch_end + timedelta(days=1)
    
    logger.info(f"Total bill allocation rows collected: {len(all_rows)}")
    
    with psycopg.connect(db_url, autocommit=True) as conn:
        # Optionally reset fact and auxiliary tables to avoid stale rows
        if reset_fact:
            with conn.cursor() as cur:
                logger.info("Resetting fact_bills_receivable and tally_loader tables (truncate)")
                cur.execute("truncate table fact_bills_receivable")
                cur.execute("truncate table tally_loader.trn_bill")
                cur.execute("truncate table tally_loader.trn_voucher")
        
        # Load into staging (legacy) and tally loader tables
        staging_count = load_stg_trn_bill(conn, all_rows)
        logger.info(f"Loaded {staging_count} rows into staging table")
        
        voucher_count, bill_count = load_tally_loader_trn_tables(conn, all_rows)
        logger.info(f"Loaded {voucher_count} vouchers and {bill_count} bill rows into tally_loader tables")
        
        # Transform and upsert into fact table using open-source logic
        fact_count = upsert_fact_bills_receivable(conn)
        logger.info(f"Upserted {fact_count} rows into fact_bills_receivable")
        
        return fact_count




