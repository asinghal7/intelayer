"""
Main entry point for running tally_db_loader as a module.

Usage:
    python -m tally_db_loader [options]
    
This is equivalent to running:
    python -m tally_db_loader.sync [options]
"""
import sys
from .sync import main as sync_main

if __name__ == "__main__":
    # Import and run the sync module's main function
    from . import sync
    sys.exit(sync.main() if hasattr(sync, 'main') else 0)

