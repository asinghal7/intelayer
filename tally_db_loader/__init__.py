"""
Tally Database Loader - Complete data synchronization from Tally to PostgreSQL.

This module provides a production-ready implementation for fetching all master
and transaction data from TallyPrime using the HTTP XML interface and loading
it into PostgreSQL tables.

Key Features:
- Full and incremental sync modes
- All master data: Groups, Ledgers, Stock Items, Units, Cost Centers, etc.
- All transaction data: Vouchers, Accounting entries, Inventory entries, Bills
- Automatic checkpoint management for incremental syncs
- Comprehensive logging and debugging utilities
- Production-ready error handling and retry logic

Usage:
    # Full sync
    python -m tally_db_loader.sync --full

    # Incremental sync (default)
    python -m tally_db_loader.sync

    # Sync specific entities
    python -m tally_db_loader.sync --entities ledgers,stock_items

    # Debug mode
    python -m tally_db_loader.debug --test-connection
"""

__version__ = "1.0.0"
__author__ = "Intelayer"

from .config import TallyLoaderConfig
from .sync import TallySync, run_sync

__all__ = ["TallyLoaderConfig", "TallySync", "run_sync", "__version__"]

