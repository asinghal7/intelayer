"""
Debugging and diagnostic utilities for Tally Database Loader.

Provides tools for:
- Testing Tally connectivity
- Inspecting raw XML responses
- Validating parsed data
- Database inspection
- Troubleshooting sync issues
"""
from __future__ import annotations
import sys
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from loguru import logger

from .config import TallyLoaderConfig
from .client import TallyLoaderClient, TallyConnectionError
from .loaders import MasterLoader, TransactionLoader
from .sync import TallySync


class TallyDebugger:
    """
    Debugging utilities for Tally Database Loader.
    
    Usage:
        debugger = TallyDebugger()
        
        # Test connection
        debugger.test_connection()
        
        # Fetch and display raw XML
        debugger.fetch_raw_xml('ledgers')
        
        # Validate parsed data
        debugger.validate_entity('ledgers')
        
        # Inspect database
        debugger.inspect_table('mst_ledger')
    """
    
    def __init__(self, config: Optional[TallyLoaderConfig] = None):
        self.config = config or TallyLoaderConfig.from_env()
        self.sync = TallySync(self.config)
    
    def test_connection(self, verbose: bool = True) -> dict:
        """
        Test connection to Tally server.
        
        Returns connection status and server info.
        """
        result = self.sync.test_connection()
        
        if verbose:
            print("\n=== Tally Connection Test ===")
            print(f"Status: {result['status']}")
            print(f"URL: {result.get('url', 'N/A')}")
            if result['status'] == 'connected':
                print(f"Company: {result.get('company', 'N/A')}")
                print(f"Response size: {result.get('response_length', 0)} bytes")
            elif result['status'] == 'failed':
                print(f"Error: {result.get('error', 'Unknown')}")
        
        return result
    
    def fetch_raw_xml(
        self,
        entity_name: str,
        save_to_file: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> str:
        """
        Fetch raw XML response from Tally for debugging.
        
        Args:
            entity_name: Entity to fetch (e.g., 'ledgers', 'vouchers')
            save_to_file: Optional path to save XML
            from_date: Start date (for transactions)
            to_date: End date (for transactions)
            
        Returns:
            Raw XML string
        """
        # Map entity names to templates
        template_map = {
            "company": "company.xml.j2",
            "groups": "groups.xml.j2",
            "ledgers": "ledgers.xml.j2",
            "stock_groups": "stock_groups.xml.j2",
            "stock_categories": "stock_categories.xml.j2",
            "units": "units.xml.j2",
            "godowns": "godowns.xml.j2",
            "stock_items": "stock_items.xml.j2",
            "cost_categories": "cost_categories.xml.j2",
            "cost_centres": "cost_centres.xml.j2",
            "voucher_types": "voucher_types.xml.j2",
            "currencies": "currencies.xml.j2",
            "vouchers": "vouchers.xml.j2",
            "vouchers_detailed": "vouchers_detailed.xml.j2",
            "closing_stock": "closing_stock.xml.j2",
        }
        
        if entity_name not in template_map:
            raise ValueError(f"Unknown entity: {entity_name}. Valid: {list(template_map.keys())}")
        
        template = template_map[entity_name]
        
        # For transaction entities, use dates
        if entity_name in ("vouchers", "vouchers_detailed", "closing_stock"):
            if from_date is None:
                from_date = date.today() - timedelta(days=30)
            if to_date is None:
                to_date = date.today()
            xml_request = self.sync._render_template(template, from_date=from_date, to_date=to_date)
        else:
            xml_request = self.sync._render_template(template)
        
        print(f"Fetching {entity_name}...")
        xml_response = self.sync.client.post_xml(xml_request)
        
        print(f"Response size: {len(xml_response)} bytes")
        
        if save_to_file:
            Path(save_to_file).write_text(xml_response, encoding="utf-8")
            print(f"Saved to: {save_to_file}")
        
        return xml_response
    
    def validate_entity(self, entity_name: str, limit: int = 5) -> dict:
        """
        Validate parsing of an entity by showing sample records.
        
        Args:
            entity_name: Entity to validate
            limit: Max records to show
            
        Returns:
            Dict with validation results
        """
        from .parsers.masters import (
            parse_company, parse_groups, parse_ledgers, parse_stock_groups,
            parse_stock_categories, parse_units, parse_godowns, parse_stock_items,
            parse_cost_categories, parse_cost_centres, parse_voucher_types, parse_currencies,
        )
        from .parsers.transactions import parse_vouchers
        
        parser_map = {
            "company": parse_company,
            "groups": parse_groups,
            "ledgers": parse_ledgers,
            "stock_groups": parse_stock_groups,
            "stock_categories": parse_stock_categories,
            "units": parse_units,
            "godowns": parse_godowns,
            "stock_items": parse_stock_items,
            "cost_categories": parse_cost_categories,
            "cost_centres": parse_cost_centres,
            "voucher_types": parse_voucher_types,
            "currencies": parse_currencies,
            "vouchers": parse_vouchers,
        }
        
        if entity_name not in parser_map:
            raise ValueError(f"Unknown entity: {entity_name}")
        
        # Fetch raw XML
        xml_response = self.fetch_raw_xml(entity_name)
        
        # Parse
        parser = parser_map[entity_name]
        parsed = parser(xml_response)
        
        # Handle special cases
        if entity_name == "ledgers":
            ledgers, opening_bills = parsed
            parsed = ledgers
            extra_info = f"Opening bills: {len(opening_bills)}"
        elif entity_name == "vouchers":
            extra_info = f"Related data: {list(parsed.keys())}"
            # Show voucher headers for sample
            parsed = parsed.get("vouchers", [])
        else:
            extra_info = None
        
        result = {
            "entity": entity_name,
            "total_records": len(parsed),
            "sample_records": parsed[:limit],
        }
        
        print(f"\n=== {entity_name.upper()} Validation ===")
        print(f"Total records: {len(parsed)}")
        if extra_info:
            print(f"Extra info: {extra_info}")
        
        print(f"\nSample records (first {min(limit, len(parsed))}):")
        for i, record in enumerate(parsed[:limit]):
            print(f"\n--- Record {i+1} ---")
            for key, value in record.items():
                if value is not None and value != "":
                    # Truncate long values
                    str_value = str(value)
                    if len(str_value) > 100:
                        str_value = str_value[:100] + "..."
                    print(f"  {key}: {str_value}")
        
        return result
    
    def inspect_database(self, verbose: bool = True) -> dict:
        """
        Inspect database tables and row counts.
        
        Returns:
            Dict with table statistics
        """
        schema = self.config.db_schema
        loader = MasterLoader(self.config)
        
        tables = [
            "mst_company",
            "mst_group",
            "mst_ledger",
            "mst_stock_group",
            "mst_stock_category",
            "mst_unit",
            "mst_godown",
            "mst_stock_item",
            "mst_cost_category",
            "mst_cost_centre",
            "mst_voucher_type",
            "mst_currency",
            "mst_opening_bill",
            "trn_voucher",
            "trn_accounting",
            "trn_inventory",
            "trn_bill",
            "trn_cost_centre",
            "trn_batch",
            "trn_closing_stock",
            "sync_checkpoint",
            "sync_log",
        ]
        
        stats = {}
        
        if verbose:
            print(f"\n=== Database Inspection ({schema}) ===")
        
        for table in tables:
            try:
                count = loader.get_row_count(f"{schema}.{table}")
                stats[table] = count
                if verbose:
                    print(f"  {table}: {count:,} rows")
            except Exception as e:
                stats[table] = f"Error: {e}"
                if verbose:
                    print(f"  {table}: ERROR - {e}")
        
        loader.close()
        return stats
    
    def inspect_table(
        self,
        table_name: str,
        limit: int = 10,
        where: Optional[str] = None,
    ) -> list[dict]:
        """
        Inspect records in a specific table.
        
        Args:
            table_name: Table to inspect (with or without schema)
            limit: Max records to show
            where: Optional WHERE clause
            
        Returns:
            List of record dicts
        """
        schema = self.config.db_schema
        full_table = table_name if "." in table_name else f"{schema}.{table_name}"
        
        loader = MasterLoader(self.config)
        
        sql = f"SELECT * FROM {full_table}"
        if where:
            sql += f" WHERE {where}"
        sql += f" LIMIT {limit}"
        
        with loader.conn.cursor() as cur:
            cur.execute(sql)
            records = cur.fetchall()
        
        print(f"\n=== {full_table} (showing {len(records)} rows) ===")
        for i, record in enumerate(records):
            print(f"\n--- Row {i+1} ---")
            for key, value in record.items():
                if value is not None:
                    str_value = str(value)
                    if len(str_value) > 100:
                        str_value = str_value[:100] + "..."
                    print(f"  {key}: {str_value}")
        
        loader.close()
        return records
    
    def get_sync_status(self) -> dict:
        """
        Get current sync status from checkpoints.
        
        Returns:
            Dict with checkpoint info for each entity
        """
        schema = self.config.db_schema
        loader = MasterLoader(self.config)
        
        with loader.conn.cursor() as cur:
            cur.execute(f"""
                SELECT entity_name, last_alter_id, last_sync_at, row_count, status, error_message
                FROM {schema}.sync_checkpoint
                ORDER BY entity_name
            """)
            checkpoints = cur.fetchall()
        
        print("\n=== Sync Status ===")
        for cp in checkpoints:
            print(f"\n{cp['entity_name']}:")
            print(f"  Last sync: {cp['last_sync_at']}")
            print(f"  Row count: {cp['row_count']}")
            print(f"  Status: {cp['status']}")
            if cp['error_message']:
                print(f"  Error: {cp['error_message']}")
        
        loader.close()
        return checkpoints
    
    def get_recent_logs(self, limit: int = 10) -> list[dict]:
        """
        Get recent sync log entries.
        
        Returns:
            List of log entries
        """
        schema = self.config.db_schema
        loader = MasterLoader(self.config)
        
        with loader.conn.cursor() as cur:
            cur.execute(f"""
                SELECT id, sync_type, entity_name, started_at, completed_at,
                       rows_processed, rows_inserted, rows_updated, status,
                       duration_seconds, error_message
                FROM {schema}.sync_log
                ORDER BY started_at DESC
                LIMIT {limit}
            """)
            logs = cur.fetchall()
        
        print(f"\n=== Recent Sync Logs (last {len(logs)}) ===")
        for log in logs:
            print(f"\n[{log['id']}] {log['sync_type']} - {log['entity_name'] or 'all'}")
            print(f"  Started: {log['started_at']}")
            print(f"  Status: {log['status']}")
            if log['duration_seconds']:
                print(f"  Duration: {log['duration_seconds']}s")
            print(f"  Rows: {log['rows_processed']} processed")
            if log['error_message']:
                print(f"  Error: {log['error_message']}")
        
        loader.close()
        return logs
    
    def close(self):
        """Close connections."""
        self.sync.close()


# CLI entry point
def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Tally Database Loader - Debug Utilities"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Debug command")
    
    # Test connection
    test_parser = subparsers.add_parser("test-connection", help="Test Tally connection")
    
    # Fetch raw XML
    fetch_parser = subparsers.add_parser("fetch-xml", help="Fetch raw XML from Tally")
    fetch_parser.add_argument("entity", help="Entity to fetch")
    fetch_parser.add_argument("--save", "-o", help="Save to file")
    fetch_parser.add_argument("--from-date", type=lambda s: date.fromisoformat(s))
    fetch_parser.add_argument("--to-date", type=lambda s: date.fromisoformat(s))
    
    # Validate parsing
    validate_parser = subparsers.add_parser("validate", help="Validate entity parsing")
    validate_parser.add_argument("entity", help="Entity to validate")
    validate_parser.add_argument("--limit", "-n", type=int, default=5)
    
    # Inspect database
    inspect_db_parser = subparsers.add_parser("inspect-db", help="Inspect database")
    
    # Inspect table
    inspect_table_parser = subparsers.add_parser("inspect-table", help="Inspect table")
    inspect_table_parser.add_argument("table", help="Table name")
    inspect_table_parser.add_argument("--limit", "-n", type=int, default=10)
    inspect_table_parser.add_argument("--where", "-w", help="WHERE clause")
    
    # Sync status
    status_parser = subparsers.add_parser("status", help="Get sync status")
    
    # Recent logs
    logs_parser = subparsers.add_parser("logs", help="Get recent sync logs")
    logs_parser.add_argument("--limit", "-n", type=int, default=10)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        debugger = TallyDebugger()
        
        if args.command == "test-connection":
            result = debugger.test_connection()
            sys.exit(0 if result["status"] == "connected" else 1)
        
        elif args.command == "fetch-xml":
            debugger.fetch_raw_xml(
                args.entity,
                save_to_file=args.save,
                from_date=args.from_date,
                to_date=args.to_date,
            )
        
        elif args.command == "validate":
            debugger.validate_entity(args.entity, limit=args.limit)
        
        elif args.command == "inspect-db":
            debugger.inspect_database()
        
        elif args.command == "inspect-table":
            debugger.inspect_table(args.table, limit=args.limit, where=args.where)
        
        elif args.command == "status":
            debugger.get_sync_status()
        
        elif args.command == "logs":
            debugger.get_recent_logs(limit=args.limit)
        
        debugger.close()
        
    except TallyConnectionError as e:
        logger.error(f"Connection error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

