# Tally Database Loader

A comprehensive Python module for synchronizing TallyPrime data to PostgreSQL, designed as part of the Intelayer project.

## Overview

Tally Database Loader fetches all master and transaction data from TallyPrime using its HTTP XML interface and loads it into a PostgreSQL database. It supports both full and incremental synchronization modes.

## Features

- **Complete Data Sync**: Synchronize all Tally master and transaction data
- **Incremental Updates**: Efficiently sync only changed data
- **Batch Processing**: Handle large date ranges without timeout issues
- **Production Ready**: Comprehensive error handling, logging, and retry logic
- **Debugging Tools**: Built-in utilities for troubleshooting

## Supported Data Types

### Master Data
- Company information
- Ledger Groups (Chart of Accounts hierarchy)
- Ledgers (Customers, Suppliers, Expenses, etc.)
- Stock Groups
- Stock Categories
- Stock Items (Inventory)
- Units of Measurement
- Godowns (Warehouses)
- Cost Categories
- Cost Centres
- Voucher Types
- Currencies

### Transaction Data
- Vouchers (Sales, Purchase, Receipt, Payment, Journal, etc.)
- Accounting Entries (Ledger postings)
- Inventory Entries (Stock movements)
- Bill Allocations (Outstanding/Receivables tracking)
- Cost Centre Allocations
- Batch Allocations
- Closing Stock

## Installation

The module is part of Intelayer and uses its dependencies. Ensure you have:

```bash
pip install -r requirements.txt
```

Key dependencies:
- `psycopg[binary]` - PostgreSQL adapter
- `lxml` - XML parsing
- `jinja2` - Template rendering
- `requests` - HTTP client
- `tenacity` - Retry logic
- `loguru` - Logging
- `python-dotenv` - Environment configuration

## Configuration

Set the following environment variables (or add to `.env`):

```bash
# Tally Connection
TALLY_URL=http://192.168.1.50:9000
TALLY_COMPANY=Your Company Name

# Database Connection
DB_URL=postgresql://user:password@localhost:5432/database

# Optional Settings
TALLY_LOADER_SCHEMA=tally_db         # PostgreSQL schema name
TALLY_BATCH_SIZE=1000                 # Records per batch
TALLY_REQUEST_TIMEOUT=300             # Timeout in seconds
TALLY_RETRY_ATTEMPTS=3                # Retry count
LOG_LEVEL=INFO                        # Logging level
```

## Quick Start

### 1. Initialize Database Schema

```bash
python -m tally_db_loader.sync --init-only
```

Or in Python:
```python
from tally_db_loader import TallySync

with TallySync() as sync:
    sync.initialize_schema()
```

### 2. Test Connection

```bash
python -m tally_db_loader.sync --test-connection
```

### 3. Run Full Sync

```bash
# Sync all data
python -m tally_db_loader.sync --mode full

# Sync with specific date range for transactions
python -m tally_db_loader.sync --mode full --from-date 2024-04-01 --to-date 2024-10-31
```

### 4. Run Incremental Sync

```bash
python -m tally_db_loader.sync --mode incremental
```

This syncs all masters and the last 7 days of transactions.

### 5. Selective Sync

```bash
# Sync only specific masters
python -m tally_db_loader.sync --mode masters --entities ledgers stock_items

# Sync only transactions
python -m tally_db_loader.sync --mode transactions --from-date 2024-04-01
```

## Python API

```python
from tally_db_loader import TallySync, run_sync
from datetime import date

# Simple sync
results = run_sync(mode="incremental")

# Full control
with TallySync() as sync:
    # Test connection
    status = sync.test_connection()
    print(f"Connected: {status['status']}")
    
    # Initialize schema
    sync.initialize_schema()
    
    # Sync all masters
    master_counts = sync.sync_masters()
    print(f"Ledgers: {master_counts['ledgers']}")
    
    # Sync specific masters
    sync.sync_masters(['ledgers', 'stock_items'])
    
    # Sync transactions for date range
    txn_counts = sync.sync_transactions(
        from_date=date(2024, 4, 1),
        to_date=date.today(),
        batch_days=30,  # Process in 30-day batches
    )
    
    # Full sync
    all_results = sync.run_full_sync()
```

## Debugging

The module includes comprehensive debugging tools:

### Command Line

```bash
# Test connection
python -m tally_db_loader.debug test-connection

# Fetch and save raw XML
python -m tally_db_loader.debug fetch-xml ledgers --save ledgers.xml

# Validate parsing
python -m tally_db_loader.debug validate ledgers --limit 10

# Inspect database
python -m tally_db_loader.debug inspect-db

# Inspect specific table
python -m tally_db_loader.debug inspect-table mst_ledger --limit 5

# View sync status
python -m tally_db_loader.debug status

# View recent sync logs
python -m tally_db_loader.debug logs --limit 10
```

### Python API

```python
from tally_db_loader.debug import TallyDebugger

debugger = TallyDebugger()

# Test connection
debugger.test_connection()

# Fetch raw XML for inspection
xml = debugger.fetch_raw_xml('ledgers', save_to_file='debug_ledgers.xml')

# Validate parsing shows sample records
debugger.validate_entity('ledgers', limit=5)

# Inspect database
debugger.inspect_database()

# Inspect specific table
debugger.inspect_table('mst_ledger', limit=10, where="parent = 'Sundry Debtors'")

# Check sync status
debugger.get_sync_status()

debugger.close()
```

## Database Schema

All tables are created in the `tally_db` schema (configurable).

### Master Tables
- `mst_company` - Company information
- `mst_group` - Ledger groups hierarchy
- `mst_ledger` - All ledgers with details
- `mst_stock_group` - Stock group hierarchy
- `mst_stock_category` - Stock categories
- `mst_stock_item` - Inventory items
- `mst_unit` - Units of measurement
- `mst_godown` - Warehouses
- `mst_cost_category` - Cost categories
- `mst_cost_centre` - Cost centres
- `mst_voucher_type` - Voucher type definitions
- `mst_currency` - Currencies
- `mst_opening_bill` - Opening bill allocations

### Transaction Tables
- `trn_voucher` - Voucher headers
- `trn_accounting` - Accounting (ledger) entries
- `trn_inventory` - Inventory entries
- `trn_bill` - Bill allocations
- `trn_cost_centre` - Cost centre allocations
- `trn_batch` - Batch allocations
- `trn_closing_stock` - Stock closing balances

### System Tables
- `sync_checkpoint` - Track sync progress
- `sync_log` - Sync operation history

### Views
- `view_bills_outstanding` - Outstanding receivables/payables
- `view_ledger_balance` - Ledger balances
- `view_daily_summary` - Daily voucher summary

## Testing

```bash
# Run unit tests
pytest tally_db_loader/tests/ -v

# Run with coverage
pytest tally_db_loader/tests/ --cov=tally_db_loader

# Run integration tests (requires Tally)
pytest tally_db_loader/tests/ -v -m integration
```

## Troubleshooting

### Connection Issues
1. Ensure TallyPrime is running
2. Verify TallyPrime is configured for XML over HTTP (F1 > Settings > Advanced)
3. Check the port (default 9000) and firewall settings
4. Use `python -m tally_db_loader.debug test-connection` to diagnose

### Timeout Errors
- Reduce `batch_days` parameter for large date ranges
- Increase `TALLY_REQUEST_TIMEOUT` environment variable
- Consider syncing specific date ranges

### Parse Errors
- Use `python -m tally_db_loader.debug fetch-xml [entity] --save debug.xml` to inspect raw XML
- Check for special characters or encoding issues
- Report persistent issues with sample XML (anonymized)

### Database Errors
- Run `python -m tally_db_loader.sync --init-only` to ensure schema exists
- Check database permissions
- Verify PostgreSQL connection string

## Architecture

```
tally_db_loader/
├── __init__.py           # Package exports
├── config.py             # Configuration management
├── client.py             # Tally HTTP client
├── sync.py               # Main sync orchestration
├── debug.py              # Debugging utilities
├── requests/             # XML request templates
│   ├── company.xml.j2
│   ├── ledgers.xml.j2
│   ├── vouchers.xml.j2
│   └── ...
├── parsers/              # XML response parsers
│   ├── __init__.py
│   ├── base.py           # Parsing utilities
│   ├── masters.py        # Master data parsers
│   └── transactions.py   # Transaction parsers
├── loaders/              # Database loaders
│   ├── __init__.py
│   ├── base.py           # Loader base class
│   ├── masters.py        # Master loaders
│   └── transactions.py   # Transaction loaders
├── models/
│   └── schema.sql        # Database DDL
└── tests/
    ├── test_parsers.py
    └── test_sync.py
```

## License

Part of Intelayer project. See main LICENSE file.

