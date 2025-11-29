"""
Transaction data loaders.

Handles upserting of all Tally transaction data into PostgreSQL.
"""
from __future__ import annotations
from datetime import date
from typing import Optional
from loguru import logger
from .base import DatabaseLoader
from ..config import TallyLoaderConfig


class TransactionLoader(DatabaseLoader):
    """
    Loader for Tally transaction data.
    
    Supports:
    - Vouchers
    - Accounting entries
    - Inventory entries
    - Bill allocations
    - Cost centre allocations
    - Batch allocations
    - Closing stock
    """
    
    def __init__(self, config: Optional[TallyLoaderConfig] = None):
        super().__init__(config)
        self.schema = self.config.db_schema
    
    def load_vouchers(self, rows: list[dict]) -> int:
        """Load voucher headers."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.trn_voucher",
            rows,
            key_columns=["guid"],
        )
        logger.info(f"Loaded {count} vouchers")
        return count
    
    def load_accounting_entries(self, rows: list[dict]) -> int:
        """
        Load accounting (ledger) entries.
        
        Note: These are linked to vouchers via voucher_guid.
        """
        if not rows:
            return 0
        
        # For accounting entries, we use insert (not upsert)
        # since they don't have a natural unique key
        # First, delete existing entries for the vouchers being loaded
        voucher_guids = list(set(r["voucher_guid"] for r in rows))
        
        with self.conn.cursor() as cur:
            # Delete in batches to avoid very long IN clauses
            batch_size = 100
            for i in range(0, len(voucher_guids), batch_size):
                batch = voucher_guids[i:i + batch_size]
                placeholders = ", ".join(["%s"] * len(batch))
                cur.execute(
                    f"DELETE FROM {self.schema}.trn_accounting WHERE voucher_guid IN ({placeholders})",
                    batch,
                )
        
        # Insert new entries
        count = self.insert_batch(f"{self.schema}.trn_accounting", rows)
        logger.info(f"Loaded {count} accounting entries")
        return count
    
    def load_inventory_entries(self, rows: list[dict]) -> int:
        """
        Load inventory entries.
        
        Note: These are linked to vouchers via voucher_guid.
        """
        if not rows:
            return 0
        
        # Delete existing entries for vouchers being loaded
        voucher_guids = list(set(r["voucher_guid"] for r in rows))
        
        with self.conn.cursor() as cur:
            batch_size = 100
            for i in range(0, len(voucher_guids), batch_size):
                batch = voucher_guids[i:i + batch_size]
                placeholders = ", ".join(["%s"] * len(batch))
                cur.execute(
                    f"DELETE FROM {self.schema}.trn_inventory WHERE voucher_guid IN ({placeholders})",
                    batch,
                )
        
        count = self.insert_batch(f"{self.schema}.trn_inventory", rows)
        logger.info(f"Loaded {count} inventory entries")
        return count
    
    def load_bill_allocations(self, rows: list[dict]) -> int:
        """
        Load bill allocations.
        
        Note: These are linked to vouchers via voucher_guid.
        """
        if not rows:
            return 0
        
        # Delete existing entries for vouchers being loaded
        voucher_guids = list(set(r["voucher_guid"] for r in rows))
        
        with self.conn.cursor() as cur:
            batch_size = 100
            for i in range(0, len(voucher_guids), batch_size):
                batch = voucher_guids[i:i + batch_size]
                placeholders = ", ".join(["%s"] * len(batch))
                cur.execute(
                    f"DELETE FROM {self.schema}.trn_bill WHERE voucher_guid IN ({placeholders})",
                    batch,
                )
        
        count = self.insert_batch(f"{self.schema}.trn_bill", rows)
        logger.info(f"Loaded {count} bill allocations")
        return count
    
    def load_cost_centre_allocations(self, rows: list[dict]) -> int:
        """
        Load cost centre allocations.
        
        Note: These are linked to vouchers via voucher_guid.
        """
        if not rows:
            return 0
        
        # Delete existing entries for vouchers being loaded
        voucher_guids = list(set(r["voucher_guid"] for r in rows))
        
        with self.conn.cursor() as cur:
            batch_size = 100
            for i in range(0, len(voucher_guids), batch_size):
                batch = voucher_guids[i:i + batch_size]
                placeholders = ", ".join(["%s"] * len(batch))
                cur.execute(
                    f"DELETE FROM {self.schema}.trn_cost_centre WHERE voucher_guid IN ({placeholders})",
                    batch,
                )
        
        count = self.insert_batch(f"{self.schema}.trn_cost_centre", rows)
        logger.info(f"Loaded {count} cost centre allocations")
        return count
    
    def load_batch_allocations(self, rows: list[dict]) -> int:
        """
        Load batch allocations.
        
        Note: These are linked to vouchers via voucher_guid.
        """
        if not rows:
            return 0
        
        # Delete existing entries for vouchers being loaded
        voucher_guids = list(set(r["voucher_guid"] for r in rows))
        
        with self.conn.cursor() as cur:
            batch_size = 100
            for i in range(0, len(voucher_guids), batch_size):
                batch = voucher_guids[i:i + batch_size]
                placeholders = ", ".join(["%s"] * len(batch))
                cur.execute(
                    f"DELETE FROM {self.schema}.trn_batch WHERE voucher_guid IN ({placeholders})",
                    batch,
                )
        
        count = self.insert_batch(f"{self.schema}.trn_batch", rows)
        logger.info(f"Loaded {count} batch allocations")
        return count
    
    def load_closing_stock(self, rows: list[dict]) -> int:
        """Load closing stock data."""
        if not rows:
            return 0
        
        count, _ = self.upsert_batch(
            f"{self.schema}.trn_closing_stock",
            rows,
            key_columns=["as_of_date", "stock_item", "godown"],
        )
        logger.info(f"Loaded {count} closing stock entries")
        return count
    
    def load_all_transaction_data(self, parsed_data: dict) -> dict:
        """
        Load all transaction data from parsed voucher response.
        
        Args:
            parsed_data: Dict from parse_vouchers() with keys:
                - vouchers
                - accounting
                - inventory
                - bills
                - cost_centres
                - batches
                
        Returns:
            Dict with counts for each entity type
        """
        counts = {
            "vouchers": self.load_vouchers(parsed_data.get("vouchers", [])),
            "accounting": self.load_accounting_entries(parsed_data.get("accounting", [])),
            "inventory": self.load_inventory_entries(parsed_data.get("inventory", [])),
            "bills": self.load_bill_allocations(parsed_data.get("bills", [])),
            "cost_centres": self.load_cost_centre_allocations(parsed_data.get("cost_centres", [])),
            "batches": self.load_batch_allocations(parsed_data.get("batches", [])),
        }
        
        total = sum(counts.values())
        logger.info(f"Loaded {total} total transaction records")
        
        return counts
    
    def delete_vouchers_in_range(self, from_date: date, to_date: date) -> int:
        """
        Delete vouchers (and related entries via CASCADE) in a date range.
        
        Useful for re-syncing a specific period.
        
        Returns:
            Number of vouchers deleted
        """
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                DELETE FROM {self.schema}.trn_voucher
                WHERE date >= %s AND date <= %s
                """,
                (from_date, to_date),
            )
            deleted = cur.rowcount
        
        logger.info(f"Deleted {deleted} vouchers from {from_date} to {to_date}")
        return deleted
    
    def clear_all_transactions(self) -> dict:
        """
        Clear ALL transaction data. Use before full sync.
        
        Deletes in order to respect foreign key constraints.
        
        Returns:
            Dict with counts per table
        """
        tables = [
            "trn_batch",
            "trn_cost_centre", 
            "trn_bill",
            "trn_inventory",
            "trn_accounting",
            "trn_voucher",
            "trn_closing_stock",
        ]
        
        counts = {}
        with self.conn.cursor() as cur:
            for table in tables:
                cur.execute(f"DELETE FROM {self.schema}.{table}")
                counts[table] = cur.rowcount
        
        logger.info(f"Cleared all transactions: {counts}")
        return counts
    
    def get_voucher_date_range(self) -> tuple[date | None, date | None]:
        """Get min and max voucher dates in database."""
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT MIN(date) as min_date, MAX(date) as max_date
                FROM {self.schema}.trn_voucher
                """
            )
            result = cur.fetchone()
            if result:
                return result["min_date"], result["max_date"]
            return None, None
    
    def get_voucher_count_by_type(self) -> dict:
        """Get voucher counts grouped by type."""
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT voucher_type, COUNT(*) as count
                FROM {self.schema}.trn_voucher
                GROUP BY voucher_type
                ORDER BY count DESC
                """
            )
            return {r["voucher_type"]: r["count"] for r in cur.fetchall()}

