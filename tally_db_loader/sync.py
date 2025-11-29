"""
Main sync orchestration for Tally Database Loader.

Provides:
- Full sync: Complete data refresh
- Incremental sync: Only changed data
- Selective sync: Specific entities only
- Date range sync: Transactions in a date range
"""
from __future__ import annotations
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from jinja2 import Template
from loguru import logger
from time import sleep

from .config import TallyLoaderConfig
from .client import TallyLoaderClient, TallyConnectionError, TallyResponseError
from .loaders import MasterLoader, TransactionLoader
from .parsers.masters import (
    parse_company,
    parse_groups,
    parse_ledgers,
    parse_stock_groups,
    parse_stock_categories,
    parse_units,
    parse_godowns,
    parse_stock_items,
    parse_cost_categories,
    parse_cost_centres,
    parse_voucher_types,
    parse_currencies,
)
from .parsers.transactions import parse_vouchers, parse_closing_stock


# Request templates directory
REQUESTS_DIR = Path(__file__).parent / "requests"


class TallySync:
    """
    Main synchronization orchestrator.
    
    Coordinates fetching data from Tally and loading it into PostgreSQL.
    
    Usage:
        sync = TallySync()
        
        # Full sync
        sync.run_full_sync()
        
        # Incremental sync
        sync.run_incremental_sync()
        
        # Sync specific entities
        sync.sync_masters(['ledgers', 'stock_items'])
        
        # Sync transactions for date range
        sync.sync_transactions(from_date=date(2024, 4, 1), to_date=date.today())
    """
    
    # Master entity configurations
    MASTER_ENTITIES = {
        "company": {
            "template": "company.xml.j2",
            "parser": parse_company,
            "loader_method": "load_company",
            "table": "mst_company",
        },
        "groups": {
            "template": "groups.xml.j2",
            "parser": parse_groups,
            "loader_method": "load_groups",
            "table": "mst_group",
        },
        "ledgers": {
            "template": "ledgers.xml.j2",
            "parser": parse_ledgers,  # Returns tuple (ledgers, opening_bills)
            "loader_method": "load_ledgers",
            "table": "mst_ledger",
            "has_opening_bills": True,
        },
        "stock_groups": {
            "template": "stock_groups.xml.j2",
            "parser": parse_stock_groups,
            "loader_method": "load_stock_groups",
            "table": "mst_stock_group",
        },
        "stock_categories": {
            "template": "stock_categories.xml.j2",
            "parser": parse_stock_categories,
            "loader_method": "load_stock_categories",
            "table": "mst_stock_category",
        },
        "units": {
            "template": "units.xml.j2",
            "parser": parse_units,
            "loader_method": "load_units",
            "table": "mst_unit",
        },
        "godowns": {
            "template": "godowns.xml.j2",
            "parser": parse_godowns,
            "loader_method": "load_godowns",
            "table": "mst_godown",
        },
        "stock_items": {
            "template": "stock_items.xml.j2",
            "parser": parse_stock_items,
            "loader_method": "load_stock_items",
            "table": "mst_stock_item",
        },
        "cost_categories": {
            "template": "cost_categories.xml.j2",
            "parser": parse_cost_categories,
            "loader_method": "load_cost_categories",
            "table": "mst_cost_category",
        },
        "cost_centres": {
            "template": "cost_centres.xml.j2",
            "parser": parse_cost_centres,
            "loader_method": "load_cost_centres",
            "table": "mst_cost_centre",
        },
        "voucher_types": {
            "template": "voucher_types.xml.j2",
            "parser": parse_voucher_types,
            "loader_method": "load_voucher_types",
            "table": "mst_voucher_type",
        },
        "currencies": {
            "template": "currencies.xml.j2",
            "parser": parse_currencies,
            "loader_method": "load_currencies",
            "table": "mst_currency",
        },
    }
    
    def __init__(self, config: Optional[TallyLoaderConfig] = None):
        self.config = config or TallyLoaderConfig.from_env()
        self.client = TallyLoaderClient(self.config)
        self.master_loader = MasterLoader(self.config)
        self.transaction_loader = TransactionLoader(self.config)
    
    def _load_template(self, template_name: str) -> str:
        """Load a request template."""
        template_path = REQUESTS_DIR / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        return template_path.read_text(encoding="utf-8")
    
    def _render_template(
        self,
        template_name: str,
        company: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> str:
        """Render a request template with variables."""
        template_str = self._load_template(template_name)
        template = Template(template_str)
        
        context = {
            "company": company or self.config.tally_company,
        }
        
        if from_date:
            context["from_date"] = from_date.strftime("%d-%b-%Y")
        if to_date:
            context["to_date"] = to_date.strftime("%d-%b-%Y")
        
        return template.render(**context)
    
    def test_connection(self) -> dict:
        """Test connection to Tally."""
        return self.client.test_connection()
    
    def initialize_schema(self):
        """Create database schema and tables if they don't exist."""
        schema_file = Path(__file__).parent / "models" / "schema.sql"
        if schema_file.exists():
            self.master_loader.execute_ddl(str(schema_file))
            logger.info("Database schema initialized")
        else:
            # Just create the schema
            self.master_loader.ensure_schema()
            logger.warning(f"Schema file not found at {schema_file}, only created schema")
    
    def sync_master(self, entity_name: str, save_xml: bool = False) -> int:
        """
        Sync a single master entity.
        
        Args:
            entity_name: Name of entity (e.g., 'ledgers', 'stock_items')
            save_xml: If True, save raw XML response for debugging
            
        Returns:
            Number of rows synced
        """
        if entity_name not in self.MASTER_ENTITIES:
            raise ValueError(f"Unknown entity: {entity_name}. Valid: {list(self.MASTER_ENTITIES.keys())}")
        
        entity_config = self.MASTER_ENTITIES[entity_name]
        
        logger.info(f"Syncing {entity_name}...")
        
        try:
            # Fetch from Tally
            xml_request = self._render_template(entity_config["template"])
            xml_response = self.client.post_xml(xml_request)
            
            # Debug: save raw XML if requested
            if save_xml:
                debug_file = Path(f"debug_{entity_name}.xml")
                debug_file.write_text(xml_response, encoding="utf-8")
                logger.debug(f"  Saved raw XML to {debug_file}")
            
            # Parse response
            parser = entity_config["parser"]
            parsed_data = parser(xml_response)
            
            # Handle ledgers special case (returns tuple)
            if entity_config.get("has_opening_bills"):
                ledgers, opening_bills = parsed_data
                loader_method = getattr(self.master_loader, entity_config["loader_method"])
                count = loader_method(ledgers)
                
                # Also load opening bills
                if opening_bills:
                    self.master_loader.load_opening_bills(opening_bills)
                    logger.info(f"  Also loaded {len(opening_bills)} opening bills")
            else:
                loader_method = getattr(self.master_loader, entity_config["loader_method"])
                count = loader_method(parsed_data)
            
            # Update checkpoint
            self.master_loader.update_checkpoint(
                entity_name,
                row_count=count,
                status="completed",
            )
            
            logger.info(f"  Synced {count} {entity_name}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to sync {entity_name}: {e}")
            self.master_loader.update_checkpoint(
                entity_name,
                status="failed",
                error_message=str(e),
            )
            raise
    
    def sync_masters(self, entities: Optional[list[str]] = None) -> dict:
        """
        Sync multiple master entities.
        
        Args:
            entities: List of entity names, or None for all
            
        Returns:
            Dict of entity_name -> row_count
        """
        entities = entities or list(self.MASTER_ENTITIES.keys())
        
        results = {}
        for entity in entities:
            try:
                results[entity] = self.sync_master(entity)
            except Exception as e:
                logger.error(f"Error syncing {entity}: {e}")
                results[entity] = 0
        
        return results
    
    def sync_transactions(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        batch_days: int = 15,
        delete_existing: bool = True,
    ) -> dict:
        """
        Sync transaction data (vouchers and related entries).
        
        Args:
            from_date: Start date (defaults to FY start)
            to_date: End date (defaults to today)
            batch_days: Days per batch to avoid timeout
            delete_existing: Whether to delete existing data in range first
            
        Returns:
            Dict with counts by entity type
        """
        # Default to current financial year
        today = date.today()
        if from_date is None:
            fy_start_year = today.year if today.month >= 4 else today.year - 1
            from_date = date(fy_start_year, 4, 1)
        if to_date is None:
            to_date = today
        
        logger.info(f"Syncing transactions from {from_date} to {to_date}")
        
        # Optionally delete existing data in range
        if delete_existing:
            deleted = self.transaction_loader.delete_vouchers_in_range(from_date, to_date)
            logger.info(f"Deleted {deleted} existing vouchers in range")
        
        # Process in batches
        total_counts = {
            "vouchers": 0,
            "accounting": 0,
            "inventory": 0,
            "bills": 0,
            "cost_centres": 0,
            "batches": 0,
        }
        
        current_date = from_date
        batch_num = 0
        
        while current_date <= to_date:
            batch_num += 1
            batch_end = min(current_date + timedelta(days=batch_days - 1), to_date)
            
            logger.info(f"  Batch {batch_num}: {current_date} to {batch_end}")
            
            try:
                # Fetch vouchers for this batch
                xml_request = self._render_template(
                    "vouchers.xml.j2",
                    from_date=current_date,
                    to_date=batch_end,
                )
                xml_response = self.client.post_xml(xml_request)
                
                # Parse all transaction data
                parsed_data = parse_vouchers(xml_response)
                
                # Load into database
                batch_counts = self.transaction_loader.load_all_transaction_data(parsed_data)
                
                # Accumulate counts
                for key, val in batch_counts.items():
                    total_counts[key] += val
                
                logger.info(f"    Loaded {batch_counts['vouchers']} vouchers")
                
            except Exception as e:
                logger.error(f"  Error processing batch {current_date} to {batch_end}: {e}")
                raise
            
            # Small delay between batches
            if current_date + timedelta(days=batch_days) <= to_date:
                sleep(0.5)
            
            current_date = batch_end + timedelta(days=1)
        
        # Update checkpoint
        self.transaction_loader.update_checkpoint(
            "transactions",
            row_count=total_counts["vouchers"],
            status="completed",
        )
        
        logger.info(f"Transaction sync complete: {total_counts}")
        return total_counts
    
    def sync_closing_stock(self, as_of_date: Optional[date] = None) -> int:
        """
        Sync closing stock as of a specific date.
        
        Args:
            as_of_date: Date for stock snapshot (defaults to today)
            
        Returns:
            Number of stock entries synced
        """
        as_of = as_of_date or date.today()
        
        logger.info(f"Syncing closing stock as of {as_of}")
        
        # Use same date for from/to to get point-in-time snapshot
        xml_request = self._render_template(
            "closing_stock.xml.j2",
            from_date=as_of,
            to_date=as_of,
        )
        xml_response = self.client.post_xml(xml_request)
        
        parsed_data = parse_closing_stock(xml_response, as_of)
        count = self.transaction_loader.load_closing_stock(parsed_data)
        
        logger.info(f"Synced {count} closing stock entries")
        return count
    
    def run_full_sync(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        include_transactions: bool = True,
        include_closing_stock: bool = True,
    ) -> dict:
        """
        Run a complete full sync of all data.
        
        Args:
            from_date: Transaction start date
            to_date: Transaction end date
            include_transactions: Whether to sync transactions
            include_closing_stock: Whether to sync closing stock
            
        Returns:
            Dict with sync results
        """
        log_id = self.master_loader.log_sync("full", status="running")
        
        try:
            results = {
                "masters": {},
                "transactions": {},
                "closing_stock": 0,
            }
            
            # Initialize schema
            self.initialize_schema()
            
            # Clear all existing transaction data before full sync to prevent duplicates
            logger.info("=== Clearing Existing Transaction Data ===")
            self.transaction_loader.clear_all_transactions()
            
            # Sync all masters
            logger.info("=== Syncing Master Data ===")
            results["masters"] = self.sync_masters()
            
            # Sync transactions
            if include_transactions:
                logger.info("=== Syncing Transactions ===")
                # Don't delete_existing since we already cleared all
                results["transactions"] = self.sync_transactions(
                    from_date, to_date, delete_existing=False
                )
            
            # Sync closing stock
            if include_closing_stock:
                logger.info("=== Syncing Closing Stock ===")
                results["closing_stock"] = self.sync_closing_stock(to_date)
            
            # Update log
            total_rows = sum(results["masters"].values()) + sum(results["transactions"].values())
            self.master_loader.update_sync_log(
                log_id,
                rows_processed=total_rows,
                status="completed",
            )
            
            logger.info("=== Full Sync Complete ===")
            return results
            
        except Exception as e:
            self.master_loader.update_sync_log(
                log_id,
                status="failed",
                error_message=str(e),
            )
            raise
    
    def run_incremental_sync(self) -> dict:
        """
        Run an incremental sync (only changed data).
        
        For masters: Compare alter_id
        For transactions: Sync recent period
        
        Returns:
            Dict with sync results
        """
        log_id = self.master_loader.log_sync("incremental", status="running")
        
        try:
            results = {
                "masters": {},
                "transactions": {},
            }
            
            # For incremental, we still sync all masters (Tally handles the diff)
            # In practice, unchanged data will just be upserted with same values
            logger.info("=== Incremental Master Sync ===")
            results["masters"] = self.sync_masters()
            
            # For transactions, sync last 7 days to catch any late edits
            logger.info("=== Incremental Transaction Sync ===")
            from_date = date.today() - timedelta(days=7)
            results["transactions"] = self.sync_transactions(
                from_date=from_date,
                delete_existing=True,  # Replace recent data
            )
            
            # Update log
            total_rows = sum(results["masters"].values()) + sum(results["transactions"].values())
            self.master_loader.update_sync_log(
                log_id,
                rows_processed=total_rows,
                status="completed",
            )
            
            logger.info("=== Incremental Sync Complete ===")
            return results
            
        except Exception as e:
            self.master_loader.update_sync_log(
                log_id,
                status="failed",
                error_message=str(e),
            )
            raise
    
    def close(self):
        """Close all connections."""
        self.client.close()
        self.master_loader.close()
        self.transaction_loader.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def run_sync(
    mode: str = "incremental",
    entities: Optional[list[str]] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    config: Optional[TallyLoaderConfig] = None,
) -> dict:
    """
    Convenience function to run sync.
    
    Args:
        mode: 'full', 'incremental', 'masters', 'transactions'
        entities: Specific entities for 'masters' mode
        from_date: Start date for transactions
        to_date: End date for transactions
        config: Optional config override
        
    Returns:
        Dict with sync results
    """
    with TallySync(config) as sync:
        if mode == "full":
            return sync.run_full_sync(from_date, to_date)
        elif mode == "incremental":
            return sync.run_incremental_sync()
        elif mode == "masters":
            return {"masters": sync.sync_masters(entities)}
        elif mode == "transactions":
            return {"transactions": sync.sync_transactions(from_date, to_date)}
        else:
            raise ValueError(f"Unknown mode: {mode}. Valid: full, incremental, masters, transactions")


# CLI entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Tally Database Loader - Sync Tally data to PostgreSQL"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "incremental", "masters", "transactions"],
        default="incremental",
        help="Sync mode (default: incremental)",
    )
    parser.add_argument(
        "--entities",
        nargs="*",
        help="Specific entities to sync (for masters mode)",
    )
    parser.add_argument(
        "--from-date",
        type=lambda s: date.fromisoformat(s),
        help="Start date for transactions (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--to-date",
        type=lambda s: date.fromisoformat(s),
        help="End date for transactions (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--init-only",
        action="store_true",
        help="Only initialize database schema, don't sync",
    )
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test Tally connection and exit",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    try:
        with TallySync() as sync:
            if args.test_connection:
                result = sync.test_connection()
                print(f"Connection test: {result}")
                sys.exit(0 if result["status"] == "connected" else 1)
            
            if args.init_only:
                sync.initialize_schema()
                print("Schema initialized successfully")
                sys.exit(0)
            
            results = run_sync(
                mode=args.mode,
                entities=args.entities,
                from_date=args.from_date,
                to_date=args.to_date,
            )
            
            print("\n=== Sync Results ===")
            for category, data in results.items():
                if isinstance(data, dict):
                    print(f"\n{category}:")
                    for entity, count in data.items():
                        print(f"  {entity}: {count}")
                else:
                    print(f"{category}: {data}")
            
    except TallyConnectionError as e:
        logger.error(f"Connection error: {e}")
        sys.exit(1)
    except TallyResponseError as e:
        logger.error(f"Tally error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Sync failed: {e}")
        sys.exit(1)

