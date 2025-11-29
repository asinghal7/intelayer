"""
Basic SQL smoke test for mst_opening_bill_allocation DDL.

This test ensures the migration file exists and contains expected columns/types.
It does not connect to a database; it's a static assertion to guard accidental edits.
"""

from pathlib import Path


def test_mst_opening_bill_allocation_migration_present():
    path = Path(__file__).resolve().parents[1] / "warehouse" / "migrations" / "0008_mst_opening_bill_allocation.sql"
    assert path.exists(), "Migration 0008_mst_opening_bill_allocation.sql must exist"
    sql = path.read_text()

    # Table name
    assert "create table if not exists mst_opening_bill_allocation" in sql.lower()

    # Required columns
    for fragment in [
        "ledger text not null",
        "name text not null",
        "bill_date date",
        "opening_balance numeric(14,2)",
        "bill_credit_period int",
        "is_advance boolean",
    ]:
        assert fragment in sql.lower(), f"Expected column fragment missing: {fragment}"

    # Indexes
    for idx in [
        "idx_mst_opening_bill_alloc_ledger",
        "idx_mst_opening_bill_alloc_name",
        "idx_mst_opening_bill_alloc_bill_date",
    ]:
        assert idx in sql, f"Expected index missing: {idx}"




