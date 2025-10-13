"""
Backfill historical daybook data.

Note: Tally's DayBook export only returns current data. This script fetches
data day-by-day, making one request per day.

Usage:
    # Backfill date range (fetches one day at a time)
    python -m agent.backfill 2024-04-01 2024-10-13
    
    # Dry run to see what would be fetched
    python -m agent.backfill 2024-04-01 2024-10-13 --dry-run
"""

from datetime import date, timedelta
import sys
import psycopg
from loguru import logger
from pathlib import Path
from adapters.tally_http.adapter import TallyHTTPAdapter
from agent.settings import TALLY_URL, TALLY_COMPANY, DB_URL
from agent.run import upsert_invoice

DAYBOOK_TEMPLATE = (
    Path(__file__).resolve().parents[1] / "adapters" / "tally_http" / "requests" / "daybook.xml.j2"
).read_text(encoding="utf-8")


def parse_date(date_str: str) -> date:
    """Parse date from YYYY-MM-DD format."""
    return date.fromisoformat(date_str)


def backfill_date_range(start_date: date, end_date: date, dry_run: bool = False):
    """Backfill by fetching one day at a time (Tally limitation)."""
    logger.info(f"Backfilling from {start_date} to {end_date}")
    
    num_days = (end_date - start_date).days + 1
    if num_days > 1:
        logger.info(f"Will fetch {num_days} days (one Tally request per day)")
    
    if dry_run:
        logger.info("[DRY RUN] Would fetch data for this range")
        return
    
    # Pass empty set to include ALL voucher types
    adapter = TallyHTTPAdapter(TALLY_URL, TALLY_COMPANY, DAYBOOK_TEMPLATE, include_types=set())
    
    current = start_date
    total_count = 0
    days_with_data = 0
    
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        while current <= end_date:
            try:
                day_count = 0
                # Fetch one day at a time (from_date = to_date)
                for inv in adapter.fetch_invoices(current, current):
                    upsert_invoice(conn, inv)
                    day_count += 1
                
                total_count += day_count
                
                if day_count > 0:
                    days_with_data += 1
                    logger.info(f"✓ {current}: {day_count} invoices")
                else:
                    logger.debug(f"  {current}: no data")
                    
            except Exception as e:
                logger.error(f"✗ Error on {current}: {e}")
                raise
            
            current += timedelta(days=1)
    
    logger.success(f"✓ Backfilled {total_count} invoices from {days_with_data} days")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    start_date = parse_date(sys.argv[1])
    end_date = parse_date(sys.argv[2])
    
    # Parse flags
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        logger.warning("DRY RUN MODE - No data will be written")
    
    # Validate dates
    if start_date > end_date:
        logger.error("Start date must be before or equal to end date")
        sys.exit(1)
    
    if end_date > date.today():
        logger.warning(f"End date {end_date} is in the future, using today instead")
        end_date = date.today()
    
    # Run backfill (always day-by-day due to Tally limitation)
    backfill_date_range(start_date, end_date, dry_run)


if __name__ == "__main__":
    main()

