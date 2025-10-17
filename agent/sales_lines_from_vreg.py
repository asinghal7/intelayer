from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
import re
import psycopg
from loguru import logger
from pathlib import Path
from adapters.tally_http.adapter import TallyHTTPAdapter
from agent.settings import TALLY_URL, TALLY_COMPANY, DB_URL

DAYBOOK_TEMPLATE = (Path(__file__).resolve().parents[1] / "adapters" / "tally_http" / "requests" / "daybook.xml.j2").read_text(encoding="utf-8")


def _ensure_migration(conn) -> None:
    sql_path = Path(__file__).resolve().parents[1] / "warehouse" / "migrations" / "0006_fact_invoice_line.sql"
    sql = sql_path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)


def _parse_qty_uom(billed_qty: str) -> tuple[float | None, str | None]:
    s = (billed_qty or "").strip()
    if not s:
        return None, None
    m = re.match(r"([0-9.+-]+)\s*([^/]+)?", s)
    if not m:
        return None, None
    q = None
    try:
        q = float(m.group(1))
    except Exception:
        q = None
    u = (m.group(2) or "").strip() or None
    return q, u


def _parse_rate(rate: str) -> float | None:
    s = (rate or "").strip()
    if not s:
        return None
    # take numeric part before "/"
    s = re.sub(r"[/].*$", "", s).strip()
    s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return None


def _print_preview_in_memory(staged_headers: list[StagedHeader], staged_lines: list[StagedLine], limit: int) -> None:
    """Print preview of staged data in memory for dry-run mode."""
    logger.info(f"=== PREVIEW (top {limit} lines) ===")
    
    # Create a mapping of voucher_guid to header info for display
    header_map = {}
    for h in staged_headers:
        key = h.guid or f"{h.vch_no}/{h.vch_date}/{h.party}"
        header_map[key] = h
    
    count = 0
    for line in staged_lines:
        if count >= limit:
            break
            
        # Find matching header
        header_key = line.voucher_guid or "unknown"
        header = header_map.get(header_key)
        
        if header:
            qty, uom = _parse_qty_uom(line.billed_qty or "")
            rate = _parse_rate(line.rate or "")
            
            logger.info(f"{header.vch_date} | {header.vch_no} | {header.party} | "
                       f"{line.stock_item_name} | {qty} {uom} | {rate} | "
                       f"{line.amount} | {line.discount or 0}")
            count += 1
    
    logger.info(f"=== END PREVIEW ({count} lines shown) ===")


@dataclass
class StagedHeader:
    guid: str | None
    vch_no: str | None
    vch_date: date
    party: str | None
    basic_amount: float
    tax_amount: float
    total_amount: float


@dataclass
class StagedLine:
    voucher_guid: str | None
    stock_item_name: str
    billed_qty: str | None
    rate: str | None
    amount: float | None
    discount: float | None


def _process_batch(from_date: date, to_date: date, *, dry_run: bool = False, preview: int | None = None) -> tuple[int, int]:
    """Process a single batch of vouchers and return (headers_count, lines_count)."""
    logger.info(f"🔍 Fetching vouchers from Tally: {from_date} to {to_date}")
    adapter = TallyHTTPAdapter(TALLY_URL, TALLY_COMPANY, DAYBOOK_TEMPLATE, include_types=set())

    vouchers = list(adapter.fetch_invoices(from_date, to_date))
    logger.info(f"📥 Fetched {len(vouchers)} vouchers from Tally")

    staged_headers: list[StagedHeader] = []
    staged_lines: list[StagedLine] = []

    for v in adapter._last_vouchers_cache:
        # headers
        subtotal = float(v.get("subtotal") or 0.0)
        total = float(v.get("total") or 0.0)
        tax = total - subtotal
        staged_headers.append(
            StagedHeader(
                guid=v.get("guid") or None,
                vch_no=v.get("vchnumber") or None,
                vch_date=v.get("date"),
                party=v.get("party") or None,
                basic_amount=subtotal,
                tax_amount=tax,
                total_amount=total,
            )
        )

        # lines
        for line in (v.get("inventory_entries") or []):
            staged_lines.append(
                StagedLine(
                    voucher_guid=v.get("guid") or None,
                    stock_item_name=(line.get("stock_item_name") or "").strip(),
                    billed_qty=line.get("billed_qty"),
                    rate=line.get("rate"),
                    amount=float(line.get("amount") or 0.0),
                    discount=float(line.get("discount") or 0.0) if line.get("discount") is not None else None,
                )
            )

    headers_count = len(staged_headers)
    lines_count = len(staged_lines)

    if dry_run:
        logger.info(f"[dry-run] {from_date} to {to_date}: headers={headers_count} lines={lines_count}")
        if preview and headers_count > 0:
            _print_preview_in_memory(staged_headers, staged_lines, preview)
        return headers_count, lines_count

    with psycopg.connect(DB_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            # stage tables
            cur.execute("truncate table stg_vreg_header;")
            cur.execute("truncate table stg_vreg_line;")

            if staged_headers:
                cur.executemany(
                    """
                    insert into stg_vreg_header(guid, vch_no, vch_date, party, basic_amount, tax_amount, total_amount)
                    values (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            h.guid,
                            h.vch_no,
                            h.vch_date,
                            h.party,
                            h.basic_amount,
                            h.tax_amount,
                            h.total_amount,
                        )
                        for h in staged_headers
                    ],
                )

            if staged_lines:
                cur.executemany(
                    """
                    insert into stg_vreg_line(voucher_guid, stock_item_name, billed_qty, rate, amount, discount)
                    values (%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            l.voucher_guid,
                            l.stock_item_name,
                            l.billed_qty,
                            l.rate,
                            l.amount,
                            l.discount,
                        )
                        for l in staged_lines
                    ],
                )

            # upsert headers into fact_invoice (reusing existing logic: ensure customer exists is already handled in agent/run.py)
            if staged_headers:
                result = cur.execute(
                    """
                    insert into fact_invoice (invoice_id, voucher_key, vchtype, date, customer_id, sp_id, subtotal, tax, total, roundoff)
                    select coalesce(h.guid, h.vch_no || '/' || h.vch_date::text || '/' || coalesce(h.party,'')) as invoice_id,
                           coalesce(h.guid, h.vch_no || '/' || h.vch_date::text || '/' || coalesce(h.party,'')) as voucher_key,
                           'Invoice',
                           h.vch_date,
                           coalesce(h.party, 'UNKNOWN') as customer_id,
                           null as sp_id,
                           h.basic_amount,
                           h.tax_amount,
                           h.total_amount,
                           0.0 as roundoff
                    from stg_vreg_header h
                    on conflict (invoice_id) do update set
                      subtotal = excluded.subtotal,
                      tax = excluded.tax,
                      total = excluded.total
                    """
                )
                logger.info(f"📝 Upserted {len(staged_headers)} headers to fact_invoice")

            # Insert lines with proper duplicate handling
            if staged_lines:
                # First, delete existing lines for these specific invoices to avoid duplicates
                # Count lines to be deleted first
                cur.execute(
                    """
                    select count(*) from fact_invoice_line 
                    where invoice_id in (
                      select coalesce(h.guid, h.vch_no || '/' || h.vch_date::text || '/' || coalesce(h.party,''))
                      from stg_vreg_header h
                    )
                    """
                )
                lines_to_delete = cur.fetchone()[0]
                
                cur.execute(
                    """
                    delete from fact_invoice_line 
                    where invoice_id in (
                      select coalesce(h.guid, h.vch_no || '/' || h.vch_date::text || '/' || coalesce(h.party,''))
                      from stg_vreg_header h
                    )
                    """
                )
                logger.info(f"🗑️ Deleted {lines_to_delete} existing lines for batch invoices")

                # Debug: Check how many lines are joinable before insertion
                cur.execute(
                    """
                    select count(*) as joinable_lines
                    from stg_vreg_line l
                    join stg_vreg_header h on h.guid = l.voucher_guid
                    join fact_invoice i on (coalesce(h.guid, h.vch_no || '/' || h.vch_date::text || '/' || coalesce(h.party,''))) = i.invoice_id
                    """
                )
                joinable_count = cur.fetchone()[0]
                logger.info(f"🔍 Joinable lines (staged: {len(staged_lines)}, joinable: {joinable_count})")

                # Debug: Find lines that fail to join
                if len(staged_lines) > joinable_count:
                    cur.execute(
                        """
                        select l.stock_item_name, l.voucher_guid, h.guid as header_guid, h.vch_no
                        from stg_vreg_line l
                        left join stg_vreg_header h on h.guid = l.voucher_guid
                        left join fact_invoice i on (coalesce(h.guid, h.vch_no || '/' || h.vch_date::text || '/' || coalesce(h.party,''))) = i.invoice_id
                        where i.invoice_id is null
                        limit 10
                        """
                    )
                    failed_lines = cur.fetchall()
                    if failed_lines:
                        logger.warning(f"⚠️ Sample of {len(failed_lines)} lines that failed to join:")
                        for row in failed_lines:
                            logger.warning(f"   Item: {row[0]}, Voucher GUID: {row[1]}, Header GUID: {row[2]}, Vch No: {row[3]}")

                # Debug: Check for potential insertion failures due to regex/data issues
                cur.execute(
                    """
                    with parsed_lines as (
                      select 
                        l.stock_item_name,
                        l.billed_qty,
                        l.rate,
                        h.vch_no,
                        h.vch_date,
                        (regexp_matches(coalesce(l.billed_qty,''), '([0-9.+-]+)[[:space:]]*([^/]*)'))[1] as parsed_qty,
                        nullif(regexp_replace(coalesce(l.rate,''), '[/].*$', ''), '') as parsed_rate
                      from stg_vreg_line l
                      join stg_vreg_header h on h.guid = l.voucher_guid
                    )
                    select * from parsed_lines
                    where parsed_qty is null or parsed_rate is null
                    limit 10
                    """
                )
                problematic_lines = cur.fetchall()
                if problematic_lines:
                    logger.warning(f"⚠️ Sample of {len(problematic_lines)} lines with parsing issues:")
                    for row in problematic_lines:
                        logger.warning(f"   Invoice: {row[3]} ({row[4]}), Item: {row[0]}, BilledQty: '{row[1]}', Rate: '{row[2]}', ParsedQty: {row[5]}, ParsedRate: {row[6]}")

                # Then insert new lines
                insert_result = cur.execute(
                    """
                    insert into fact_invoice_line (
                      invoice_id, sku_id, sku_name, qty, uom, rate, discount, line_basic, line_tax, line_total
                    )
                    select
                      i.invoice_id,
                      ds.item_id as sku_id,
                      l.stock_item_name,
                      (regexp_matches(coalesce(l.billed_qty,''), '([0-9.+-]+)[[:space:]]*([^/]*)'))[1]::numeric as qty,
                      nullif((regexp_matches(coalesce(l.billed_qty,''), '([0-9.+-]+)[[:space:]]*([^/]*)'))[2], '') as uom,
                      nullif(regexp_replace(coalesce(l.rate,''), '[/].*$', ''), '')::numeric as rate,
                      null::numeric as discount,
                      l.amount as line_basic,
                      round(coalesce((l.amount / nullif(sb.sum_line_basic,0)) * coalesce(h.tax_amount,0),0),2) as line_tax,
                      round(l.amount + coalesce((l.amount / nullif(sb.sum_line_basic,0)) * coalesce(h.tax_amount,0),0),2) as line_total
                    from stg_vreg_line l
                    join stg_vreg_header h on h.guid = l.voucher_guid
                    join fact_invoice i on (coalesce(h.guid, h.vch_no || '/' || h.vch_date::text || '/' || coalesce(h.party,''))) = i.invoice_id
                    left join (
                      select h.guid, sum(l.amount) as sum_line_basic
                      from stg_vreg_line l
                      join stg_vreg_header h on h.guid = l.voucher_guid
                      group by h.guid
                    ) sb on sb.guid = h.guid
                    left join dim_item ds on lower(ds.name) = lower(l.stock_item_name)
                    """
                )
                
                # Get the actual number of rows inserted
                inserted_count = cur.rowcount
                logger.info(f"📝 Inserted {inserted_count} lines to fact_invoice_line (staged: {len(staged_lines)}, joinable: {joinable_count})")

            # Verify the data was actually inserted
            with conn.cursor() as verify_cur:
                verify_cur.execute(
                    """
                    select count(*) as header_count from fact_invoice 
                    where date between %s and %s
                    """,
                    (from_date, to_date)
                )
                header_count = verify_cur.fetchone()[0]
                
                verify_cur.execute(
                    """
                    select count(*) as line_count from fact_invoice_line fil
                    join fact_invoice fi on fil.invoice_id = fi.invoice_id
                    where fi.date between %s and %s
                    """,
                    (from_date, to_date)
                )
                line_count = verify_cur.fetchone()[0]
                
                logger.info(f"✅ Verified in DB: {header_count} headers, {line_count} lines for {from_date} to {to_date}")

            if preview and headers_count > 0:
                with conn.cursor() as c2:
                    c2.execute(
                        """
                        select fi.date, fi.voucher_key as vch_no, dc.name as customer,
                               fil.sku_name, fil.qty, fil.uom, fil.rate,
                               fil.line_basic, fil.line_tax, fil.line_total
                        from fact_invoice fi
                        join fact_invoice_line fil on fil.invoice_id = fi.invoice_id
                        left join dim_customer dc on dc.customer_id = fi.customer_id
                        where fi.date between %s and %s
                        order by fi.date desc, fi.voucher_key
                        limit %s
                        """,
                        (from_date, to_date, preview),
                    )
                    rows = c2.fetchall()
                    for r in rows:
                        logger.info(r)

    return headers_count, lines_count


def load_sales_lines(from_date: date, to_date: date, *, dry_run: bool = False, preview: int | None = None) -> None:
    """Load sales lines with automatic batching for large date ranges."""
    import time
    
    # Run migration once at the start (not on every batch)
    if not dry_run:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            _ensure_migration(conn)
    
    # Calculate total days and determine if batching is needed
    total_days = (to_date - from_date).days + 1
    batch_size = 15
    
    if total_days <= batch_size:
        # Small range - process in one go
        logger.info(f"Processing {total_days} days in single batch: {from_date} to {to_date}")
        _process_batch(from_date, to_date, dry_run=dry_run, preview=preview)
        return
    
    # Large range - process in batches
    logger.info(f"Processing {total_days} days in batches of {batch_size}: {from_date} to {to_date}")
    
    total_headers = 0
    total_lines = 0
    batch_num = 1
    
    current_date = from_date
    while current_date <= to_date:
        # Calculate batch end date
        batch_end = min(current_date + timedelta(days=batch_size - 1), to_date)
        
        logger.info(f"🔄 Processing batch {batch_num}: {current_date} to {batch_end}")
        
        try:
            headers, lines = _process_batch(current_date, batch_end, dry_run=dry_run, preview=preview)
            total_headers += headers
            total_lines += lines
            
            logger.info(f"✅ Batch {batch_num} completed: {headers} headers, {lines} lines")
            
        except Exception as e:
            logger.error(f"❌ Batch {batch_num} failed: {e}")
            raise
        
        # Move to next batch
        current_date = batch_end + timedelta(days=1)
        batch_num += 1
        
        # Small pause between batches to avoid overwhelming the system
        if not dry_run and current_date <= to_date:
            time.sleep(1)
    
    logger.info(f"🎉 All batches completed! Total: {total_headers} headers, {total_lines} lines")
    
    # Final verification - check what's actually in the database
    if not dry_run:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select count(*) as total_headers from fact_invoice 
                    where date between %s and %s
                    """,
                    (from_date, to_date)
                )
                db_header_count = cur.fetchone()[0]
                
                cur.execute(
                    """
                    select count(*) as total_lines from fact_invoice_line fil
                    join fact_invoice fi on fil.invoice_id = fi.invoice_id
                    where fi.date between %s and %s
                    """,
                    (from_date, to_date)
                )
                db_line_count = cur.fetchone()[0]
                
                # Also get total lines across all dates to see if there's a broader issue
                cur.execute("select count(*) from fact_invoice_line")
                total_lines_all_dates = cur.fetchone()[0]
                
                logger.info(f"🔍 Final DB verification: {db_header_count} headers, {db_line_count} lines in date range {from_date} to {to_date}")
                logger.info(f"🔍 Total lines in fact_invoice_line table: {total_lines_all_dates}")
                logger.info(f"📊 Processed vs DB: Headers {total_headers} vs {db_header_count}, Lines {total_lines} vs {db_line_count}")


def main(argv: list[str] | None = None) -> None:
    import argparse
    parser = argparse.ArgumentParser("sales-lines-from-vreg")
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--lookback-days", type=int)
    g.add_argument("--from", dest="from_date")
    parser.add_argument("--to", dest="to_date")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preview", type=int)
    args = parser.parse_args(argv)

    to_d = date.today()
    if args.to_date:
        to_d = date.fromisoformat(args.to_date)
    if args.from_date:
        from_d = date.fromisoformat(args.from_date)
    elif args.lookback_days:
        from_d = to_d - timedelta(days=args.lookback_days)
    else:
        from_d = to_d - timedelta(days=7)

    load_sales_lines(from_d, to_d, dry_run=args.dry_run, preview=args.preview)


if __name__ == "__main__":
    main()


