"""
Entrypoint to populate fact_bills_receivable from Tally's Outstanding Receivables report.

This is more accurate than reconstructing from transactions because:
1. Tally provides the correct pending amounts directly
2. Includes all bills, even those created before the date range
3. No need to handle orphaned payments or complex transaction logic

Usage:
    python -m run_bills_receivable_from_outstanding
    
Environment variables:
    TALLY_URL: Tally server URL (default: http://localhost:9000)
    TALLY_COMPANY: Company name in Tally
    DB_URL: PostgreSQL connection string
"""
from __future__ import annotations
import sys
from datetime import date
from loguru import logger
import psycopg
from agent.settings import TALLY_URL, TALLY_COMPANY, DB_URL
from adapters.tally_http.ar_ap.adapter import TallyARAPAdapter
from adapters.tally_http.ar_ap.parser import parse_outstanding_receivables

logger.remove()
logger.add(sys.stderr, level="INFO")


def main():
    # Fetch outstanding receivables as of today
    as_of_date = date.today()
    
    logger.info(f"Fetching Outstanding Receivables as of {as_of_date}")
    
    adapter = TallyARAPAdapter(TALLY_URL, TALLY_COMPANY)
    
    try:
        # Fetch Outstanding Receivables report from Tally
        xml = adapter.fetch_outstanding_receivables_xml(as_of_date)
        rows = parse_outstanding_receivables(xml)
        logger.info(f"Parsed {len(rows)} outstanding receivable bills")
        
        # Upsert into fact_bills_receivable
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            from agent.etl_ar_ap.loader import upsert_fact_bills_receivable_from_outstanding
            
            fact_count = upsert_fact_bills_receivable_from_outstanding(conn, rows)
            logger.info(f"Upserted {fact_count} rows into fact_bills_receivable")
        
        logger.info("✓ Bills receivable pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()



