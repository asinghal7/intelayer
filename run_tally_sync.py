#!/usr/bin/env python3
"""
Convenience script to run Tally Database Loader sync.

This script provides a simple way to sync Tally data to PostgreSQL.

Usage:
    # Full sync (default) - syncs entire financial year
    python run_tally_sync.py
    
    # Incremental sync - masters + last 7 days of transactions
    python run_tally_sync.py --incremental
    
    # Masters only
    python run_tally_sync.py --masters-only
    
    # Sync specific date range
    python run_tally_sync.py --from-date 2024-04-01 --to-date 2024-10-31
    
    # Test connection
    python run_tally_sync.py --test
    
    # Initialize database only
    python run_tally_sync.py --init-db
"""
import sys
import argparse
from datetime import date
from loguru import logger

# Add project root to path for imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tally_db_loader import TallySync, TallyLoaderConfig
from tally_db_loader.client import TallyConnectionError, TallyResponseError


def main():
    parser = argparse.ArgumentParser(
        description="Sync Tally data to PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    # Mode flags
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Run incremental sync (masters + last 7 days of transactions)",
    )
    parser.add_argument(
        "--masters-only",
        action="store_true",
        help="Sync only master data",
    )
    parser.add_argument(
        "--transactions-only",
        action="store_true",
        help="Sync only transactions",
    )
    
    # Date range
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
    
    # Utility flags
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test Tally connection and exit",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database schema only",
    )
    parser.add_argument(
        "--batch-days",
        type=int,
        default=30,
        help="Days per transaction batch (default: 30)",
    )
    
    # Logging
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress output except errors",
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logger.remove()
    if args.quiet:
        logger.add(sys.stderr, level="ERROR")
    elif args.verbose:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO")
    
    try:
        config = TallyLoaderConfig.from_env()
        
        # Validate config
        errors = config.validate()
        if errors:
            for err in errors:
                logger.error(f"Configuration error: {err}")
            return 1
        
        with TallySync(config) as sync:
            # Test connection
            if args.test:
                result = sync.test_connection()
                if result["status"] == "connected":
                    print(f"✓ Connected to Tally at {result['url']}")
                    print(f"  Company: {result.get('company', 'N/A')}")
                    if result.get('groups_found'):
                        print(f"  Ledger groups found: {result['groups_found']}")
                    if result.get('response_length'):
                        print(f"  Response size: {result['response_length']} bytes")
                    return 0
                elif result["status"] == "connected_unknown":
                    print(f"⚠ Connected to Tally at {result['url']} but got unexpected response")
                    print(f"  {result.get('message', '')}")
                    return 0
                else:
                    print(f"✗ Connection failed: {result.get('error', 'Unknown error')}")
                    return 1
            
            # Initialize database only
            if args.init_db:
                print("Initializing database schema...")
                sync.initialize_schema()
                print("✓ Database schema initialized")
                return 0
            
            # Run sync
            print("=" * 60)
            print("TALLY DATABASE LOADER")
            print("=" * 60)
            print(f"Tally URL: {config.tally_url}")
            print(f"Company: {config.tally_company}")
            print(f"Database: {config.db_url.split('@')[-1] if '@' in config.db_url else config.db_url}")
            print("=" * 60)
            
            # Initialize schema first
            sync.initialize_schema()
            
            if args.masters_only:
                print("\nSyncing MASTERS only...")
                results = {"masters": sync.sync_masters()}
            elif args.transactions_only:
                print("\nSyncing TRANSACTIONS only...")
                results = {"transactions": sync.sync_transactions(
                    from_date=args.from_date,
                    to_date=args.to_date,
                    batch_days=args.batch_days,
                )}
            elif args.incremental:
                print("\nRunning INCREMENTAL SYNC (masters + last 7 days)...")
                results = sync.run_incremental_sync()
            else:
                # Default: Full sync for entire financial year
                print("\nRunning FULL SYNC (entire financial year)...")
                results = sync.run_full_sync(
                    from_date=args.from_date,
                    to_date=args.to_date,
                )
            
            # Print results
            print("\n" + "=" * 60)
            print("SYNC RESULTS")
            print("=" * 60)
            
            if "masters" in results:
                print("\nMaster Data:")
                for entity, count in results["masters"].items():
                    print(f"  {entity}: {count:,} records")
            
            if "transactions" in results:
                print("\nTransactions:")
                for entity, count in results["transactions"].items():
                    print(f"  {entity}: {count:,} records")
            
            if "closing_stock" in results:
                print(f"\nClosing Stock: {results['closing_stock']:,} records")
            
            print("\n✓ Sync completed successfully!")
            return 0
            
    except TallyConnectionError as e:
        logger.error(f"Connection error: {e}")
        print(f"\n✗ Failed to connect to Tally: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure TallyPrime is running")
        print("  2. Check TALLY_URL in your .env file")
        print("  3. Verify TallyPrime HTTP server is enabled (F1 > Settings > Advanced)")
        return 1
        
    except TallyResponseError as e:
        logger.error(f"Tally error: {e}")
        print(f"\n✗ Tally returned an error: {e}")
        return 1
        
    except KeyboardInterrupt:
        print("\n\nSync cancelled by user")
        return 130
        
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"\n✗ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

