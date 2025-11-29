# Tally Database Loader

A production-ready Python module for synchronizing TallyPrime data to PostgreSQL, designed as part of the Intelayer project.

## Overview

Tally Database Loader fetches all master and transaction data from TallyPrime using its HTTP XML interface and loads it into a PostgreSQL database. It supports full and incremental synchronization modes with robust error handling.

## Quick Start

```bash
# Test connection
python run_tally_sync.py --test

# Full sync (default) - syncs entire financial year
python run_tally_sync.py

# Sync masters only
python run_tally_sync.py --masters-only

# Sync specific date range
python run_tally_sync.py --from-date 2024-04-01 --to-date 2025-03-31

# Incremental sync (masters + last 7 days)
python run_tally_sync.py --incremental
```

## Features

- **Complete Data Sync**: All Tally master and transaction data
- **Incremental Updates**: Efficiently sync only recent changes
- **Batch Processing**: Handle large date ranges without timeout
- **Duplicate Prevention**: Clears existing data before full sync
- **Production Ready**: Comprehensive error handling, logging, retry logic
- **Debugging Tools**: Built-in utilities for troubleshooting

## Supported Data Types

### Master Data (12 entities)
| Entity | Description |
|--------|-------------|
| Company | Company information |
| Groups | Ledger groups (Chart of Accounts hierarchy) |
| Ledgers | Customers, Suppliers, Expenses, etc. |
| Stock Groups | Inventory group hierarchy |
| Stock Categories | Stock classification |
| Stock Items | Inventory items with details |
| Units | Units of measurement |
| Godowns | Warehouses/locations |
| Cost Categories | Cost category definitions |
| Cost Centres | Cost centre definitions |
| Voucher Types | Voucher type configurations |
| Currencies | Currency definitions |

### Transaction Data (6 entities)
| Entity | Description |
|--------|-------------|
| Vouchers | Sales, Purchase, Receipt, Payment, Journal, etc. |
| Accounting Entries | Ledger postings per voucher |
| Inventory Entries | Stock movements per voucher |
| Bill Allocations | Outstanding/receivables tracking |
| Batch Allocations | Batch-wise stock tracking |
| Closing Stock | Period-end stock balances |

## Configuration

Set environment variables or add to `.env`:

```bash
# Required
TALLY_URL=http://192.168.1.50:9000
TALLY_COMPANY=Your Company Name
DB_URL=postgresql://user:password@localhost:5432/database

# Optional
TALLY_LOADER_SCHEMA=tally_db         # PostgreSQL schema (default: tally_db)
TALLY_REQUEST_TIMEOUT=300             # Request timeout in seconds
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `python run_tally_sync.py` | Full sync (entire FY) |
| `python run_tally_sync.py --test` | Test Tally connection |
| `python run_tally_sync.py --init-db` | Initialize database schema only |
| `python run_tally_sync.py --masters-only` | Sync master data only |
| `python run_tally_sync.py --incremental` | Sync masters + last 7 days |
| `python run_tally_sync.py --from-date YYYY-MM-DD --to-date YYYY-MM-DD` | Sync specific date range |

## Database Schema

All tables are created in the `tally_db` schema.

### Master Tables
- `mst_company`, `mst_group`, `mst_ledger`, `mst_stock_group`
- `mst_stock_category`, `mst_stock_item`, `mst_unit`, `mst_godown`
- `mst_cost_category`, `mst_cost_centre`, `mst_voucher_type`, `mst_currency`

### Transaction Tables
- `trn_voucher` - Voucher headers with CASCADE delete to child tables
- `trn_accounting` - Accounting entries
- `trn_inventory` - Inventory entries
- `trn_bill` - Bill allocations
- `trn_cost_centre` - Cost centre allocations
- `trn_batch` - Batch allocations
- `trn_closing_stock` - Closing stock snapshots

### System Tables
- `sync_checkpoint` - Track sync progress per entity
- `sync_log` - Operation history

## Python API

```python
from tally_db_loader import TallySync, TallyLoaderConfig
from datetime import date

config = TallyLoaderConfig.from_env()

with TallySync(config) as sync:
    # Test connection
    result = sync.test_connection()
    
    # Initialize schema
    sync.initialize_schema()
    
    # Full sync
    results = sync.run_full_sync()
    
    # Or sync selectively
    sync.sync_masters(['ledgers', 'stock_items'])
    sync.sync_transactions(from_date=date(2024, 4, 1))
```

## Architecture

```
tally_db_loader/
├── __init__.py           # Package exports
├── config.py             # Configuration management
├── client.py             # Tally HTTP client with retry logic
├── sync.py               # Main sync orchestration
├── debug.py              # Debugging utilities
├── requests/             # XML request templates (Jinja2)
│   ├── company.xml.j2
│   ├── ledgers.xml.j2
│   ├── vouchers.xml.j2
│   └── ...
├── parsers/              # XML response parsers
│   ├── base.py           # Common parsing utilities
│   ├── masters.py        # Master data parsers
│   └── transactions.py   # Transaction parsers
├── loaders/              # Database loaders
│   ├── base.py           # Upsert/insert utilities
│   ├── masters.py        # Master data loaders
│   └── transactions.py   # Transaction loaders
├── models/
│   └── schema.sql        # PostgreSQL DDL
└── tests/
    ├── test_parsers.py
    └── test_sync.py
```

## Known Limitations

1. **Opening Bills** (`mst_opening_bill`): Not populated in current TDL approach. Use trn_bill for bill tracking.

2. **Cost Centres**: Will be empty if cost centres are not used in the Tally company.

## Troubleshooting

### Connection Issues
```bash
python run_tally_sync.py --test
```
- Ensure TallyPrime is running
- Check TallyPrime HTTP server is enabled (F1 > Settings > Advanced)
- Verify firewall allows port 9000

### Timeout Errors
- Reduce batch size by using `--from-date` and `--to-date` for smaller ranges
- The sync automatically processes in 15-day batches

### Duplicate Data
- Full sync (`python run_tally_sync.py`) clears all transaction data before sync
- Use `--incremental` for daily updates without clearing data

## Sample Output

```
============================================================
TALLY DATABASE LOADER
============================================================
Tally URL: http://192.168.0.189:9000
Company: Ashirvad Sales (23-24/24-25)
Database: localhost:5432/intelayer
============================================================

Running FULL SYNC (entire financial year)...

Master Data:
  company: 1 records
  groups: 60 records
  ledgers: 1,265 records
  stock_items: 564 records
  ...

Transactions:
  vouchers: 10,450 records
  accounting: 31,200 records
  inventory: 15,800 records
  bills: 22,400 records
  ...

✓ Sync completed successfully!
```

## License

Part of Intelayer project.
