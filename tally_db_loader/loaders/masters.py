"""
Master data loaders.

Handles upserting of all Tally master data into PostgreSQL.
"""
from __future__ import annotations
from typing import Optional
from loguru import logger
from .base import DatabaseLoader
from ..config import TallyLoaderConfig


class MasterLoader(DatabaseLoader):
    """
    Loader for Tally master data.
    
    Supports all master types:
    - Company
    - Groups
    - Ledgers (with opening bills)
    - Stock Groups
    - Stock Categories
    - Units
    - Godowns
    - Stock Items
    - Cost Categories
    - Cost Centres
    - Voucher Types
    - Currencies
    """
    
    def __init__(self, config: Optional[TallyLoaderConfig] = None):
        super().__init__(config)
        self.schema = self.config.db_schema
    
    def load_company(self, rows: list[dict]) -> int:
        """Load company master data."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_company",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} companies")
        return count
    
    def load_groups(self, rows: list[dict]) -> int:
        """Load ledger groups."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_group",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} groups")
        return count
    
    def load_ledgers(self, rows: list[dict]) -> int:
        """Load ledgers."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_ledger",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} ledgers")
        return count
    
    def load_opening_bills(self, rows: list[dict]) -> int:
        """Load opening bill allocations from ledger masters."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_opening_bill",
            rows,
            key_columns=["ledger", "name"],
        )
        logger.info(f"Loaded {count} opening bills")
        return count
    
    def update_ledger_opening_balances_from_bills(self) -> int:
        """
        Update mst_ledger.opening_balance from the sum of mst_opening_bill records.
        
        This corrects the opening balance which is incorrectly fetched from TDL
        (TDL's $OpeningBalance returns today's opening, not FY start opening).
        
        - Ledgers with bills in mst_opening_bill: opening_balance = SUM(bill.opening_balance)
        - Ledgers without bills: opening_balance = 0
        
        Returns:
            Number of ledgers updated
        """
        sql = f"""
            WITH bill_totals AS (
                SELECT 
                    ledger_lower,
                    SUM(opening_balance) AS total_opening
                FROM {self.schema}.mst_opening_bill
                GROUP BY ledger_lower
            )
            UPDATE {self.schema}.mst_ledger l
            SET opening_balance = COALESCE(bt.total_opening, 0)
            FROM (
                SELECT 
                    ml.name_lower,
                    bt.total_opening
                FROM {self.schema}.mst_ledger ml
                LEFT JOIN bill_totals bt ON bt.ledger_lower = ml.name_lower
            ) AS bt
            WHERE l.name_lower = bt.name_lower
        """
        
        with self.conn.cursor() as cur:
            cur.execute(sql)
            updated = cur.rowcount
        
        logger.info(f"Updated opening balances for {updated} ledgers from bill allocations")
        return updated
    
    def load_stock_groups(self, rows: list[dict]) -> int:
        """Load stock groups."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_stock_group",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} stock groups")
        return count
    
    def load_stock_categories(self, rows: list[dict]) -> int:
        """Load stock categories."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_stock_category",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} stock categories")
        return count
    
    def load_units(self, rows: list[dict]) -> int:
        """Load units of measurement."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_unit",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} units")
        return count
    
    def load_godowns(self, rows: list[dict]) -> int:
        """Load godowns (warehouses)."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_godown",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} godowns")
        return count
    
    def load_stock_items(self, rows: list[dict]) -> int:
        """Load stock items."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_stock_item",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} stock items")
        return count
    
    def load_cost_categories(self, rows: list[dict]) -> int:
        """Load cost categories."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_cost_category",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} cost categories")
        return count
    
    def load_cost_centres(self, rows: list[dict]) -> int:
        """Load cost centres."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_cost_centre",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} cost centres")
        return count
    
    def load_voucher_types(self, rows: list[dict]) -> int:
        """Load voucher types."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_voucher_type",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} voucher types")
        return count
    
    def load_currencies(self, rows: list[dict]) -> int:
        """Load currencies."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.mst_currency",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} currencies")
        return count
    
    def get_max_alter_id(self, table_name: str) -> int | None:
        """Get maximum alter_id from a table."""
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT MAX(alter_id) as max_id FROM {self.schema}.{table_name}")
            result = cur.fetchone()
            return result["max_id"] if result else None

