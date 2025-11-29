from __future__ import annotations
import os
from loguru import logger
from agent.settings import DB_URL, TALLY_URL, TALLY_COMPANY
from agent.etl_ar_ap.loader import run_mst_opening_bill_allocation_pipeline


def main() -> None:
    db_url = os.getenv("DB_URL", DB_URL)
    tally_url = os.getenv("TALLY_URL", TALLY_URL)
    tally_company = os.getenv("TALLY_COMPANY", TALLY_COMPANY)

    logger.info("Starting mst_opening_bill_allocation load")
    count = run_mst_opening_bill_allocation_pipeline(db_url, tally_url, tally_company)
    logger.info(f"Completed. Rows inserted: {count}")


if __name__ == "__main__":
    main()




