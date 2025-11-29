"""
Database models for Tally Database Loader.

This module contains the PostgreSQL schema definition and related utilities.
"""
from pathlib import Path

# Path to schema file
SCHEMA_FILE = Path(__file__).parent / "schema.sql"


def get_schema_sql() -> str:
    """Get the full schema SQL."""
    return SCHEMA_FILE.read_text(encoding="utf-8")

