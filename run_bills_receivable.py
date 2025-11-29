from __future__ import annotations
import os
from datetime import date
from loguru import logger
from agent.settings import DB_URL, TALLY_URL, TALLY_COMPANY
from agent.etl_ar_ap.loader import run_bills_receivable_pipeline


def get_fy_start() -> date:
    """
    Get financial year start for bills receivable pipeline.
    
    IMPORTANT: This must match the opening balance date in mst_opening_bill_allocation.
    If opening balances are as of 1-Apr-2023, transactions must start from 1-Apr-2023
    to capture all adjustments made since then.
    
    Override with FROM_DT env var if needed.
    """
    # Default to FY 2023-24 start to match opening balance date
    # Change this if your opening balances are from a different date
    return date(2023, 4, 1)


def main() -> None:
    db_url = os.getenv("DB_URL", DB_URL)
    tally_url = os.getenv("TALLY_URL", TALLY_URL)
    tally_company = os.getenv("TALLY_COMPANY", TALLY_COMPANY)
    
    # Parse date range from env vars or default to FY start to today
    from_dt_str = os.getenv("FROM_DT")
    to_dt_str = os.getenv("TO_DT")
    
    if from_dt_str:
        from_dt = date.fromisoformat(from_dt_str)
    else:
        from_dt = get_fy_start()
    
    if to_dt_str:
        to_dt = date.fromisoformat(to_dt_str)
    else:
        to_dt = date.today()
    
    # Batch size (days per batch) - smaller batches prevent Tally crashes
    batch_days = int(os.getenv("BATCH_DAYS", "15"))
    
    logger.info(f"Starting bills receivable pipeline from {from_dt} to {to_dt} (batch size: {batch_days} days)")
    logger.info(f"NOTE: Ensure mst_opening_bill_allocation opening date matches from_dt ({from_dt})")
    count = run_bills_receivable_pipeline(db_url, tally_url, tally_company, from_dt, to_dt, batch_days=batch_days)
    logger.info(f"Completed. Rows processed: {count}")


if __name__ == "__main__":
    main()

