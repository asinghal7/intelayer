"""
Clear and reload data for a specific date range.

This script makes it easy to:
1. Delete data for a date range
2. Backfill the same date range with fresh data

Useful when you've made code changes and want to reload historical data.

Usage:
    # Clear and reload specific date range
    python -m agent.clear_and_reload 2024-04-01 2024-10-13
    
    # Dry run to see what would be deleted (doesn't actually delete or reload)
    python -m agent.clear_and_reload 2024-04-01 2024-10-13 --dry-run
"""

import sys
import psycopg
from datetime import date
from loguru import logger
from agent.settings import DB_URL
from agent.backfill import parse_date, backfill_date_range


def clear_data(start_date: date, end_date: date, dry_run: bool = False):
    """Delete invoice data for the specified date range."""
    logger.info(f"Clearing data from {start_date} to {end_date}")
    
    if dry_run:
        logger.info("[DRY RUN] Would delete invoices in this date range")
        return 0
    
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM fact_invoice 
                WHERE date >= %s AND date <= %s
            """, (start_date, end_date))
            
            deleted = cur.rowcount
            logger.info(f"✓ Deleted {deleted} invoices")
            return deleted


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    start_date = parse_date(sys.argv[1])
    end_date = parse_date(sys.argv[2])
    
    # Parse flags
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        logger.warning("DRY RUN MODE - No data will be deleted or written")
    
    # Validate dates
    if start_date > end_date:
        logger.error("Start date must be before or equal to end date")
        sys.exit(1)
    
    if end_date > date.today():
        logger.warning(f"End date {end_date} is in the future, using today instead")
        end_date = date.today()
    
    logger.info(f"Clear and reload: {start_date} to {end_date}")
    
    # Step 1: Clear existing data
    logger.info("Step 1/2: Clearing existing data...")
    deleted = clear_data(start_date, end_date, dry_run)
    
    # Step 2: Reload data
    logger.info("Step 2/2: Reloading fresh data...")
    backfill_date_range(start_date, end_date, dry_run)
    
    logger.success(f"✓ Clear and reload complete!")


if __name__ == "__main__":
    main()

