# Ledger Masters Implementation Summary

## Overview

This document summarizes the implementation of ledger group master tables and customer ledger group assignment functionality.

## What Was Implemented

### 1. Database Schema Changes

**Migration: `warehouse/migrations/0007_ledger_masters.sql`**

- Created `dim_ledger_group` table for ledger group hierarchy
  - Supports parent-child relationships (e.g., Sundry Debtors → North Zone Debtors → Delhi Customers)
  - Includes Tally GUID, name, parent_name, alter_id, and updated_at fields
  - Indexed for performance on guid, name, and parent_name

- Added `ledger_group_name` column to `dim_customer`
  - Links customers to their ledger groups
  - Enables customer segmentation and reporting
  - Indexed for efficient queries

### 2. Tally Integration

**New Files:**
- `adapters/tally_http/requests/ledgers.xml.j2` - XML request template to fetch ledger masters from Tally
- `adapters/tally_http/ledgers_parser.py` - Parser for ledger XML data

**Parser Functions:**
- `parse_ledgers()` - Extract individual ledgers with their parent groups
- `parse_ledger_groups()` - Extract explicit group definitions
- `extract_ledger_groups_from_ledgers()` - Fallback to extract groups from ledger parent names
- `parse_ledger_masters()` - Main entry point that combines all parsing logic

### 3. ETL Script

**New File: `agent/ledger_masters.py`**

**Features:**
- Fetch ledger data from Tally via HTTP
- Load from local XML files for testing
- Upsert ledger groups into `dim_ledger_group`
- Update customer ledger group assignments in `dim_customer`
- Preview functionality with `--preview` flag
- Dry-run mode with `--dry-run` flag

**Command-line Options:**
```bash
python -m agent.ledger_masters --from-tally              # Fetch from Tally
python -m agent.ledger_masters --from-file ledgers.xml   # Load from file
python -m agent.ledger_masters --from-tally --dry-run    # Preview without writing
python -m agent.ledger_masters --from-tally --preview 50 # Show 50 sample records
```

### 4. Documentation

**New Files:**
- `LEDGER_MASTER_USAGE.md` - Comprehensive usage guide with examples, queries, and troubleshooting
- `LEDGER_MASTERS_IMPLEMENTATION.md` - This file (implementation summary)

**Updated Files:**
- `DATABASE_SCHEMA.md` - Added dim_ledger_group table and dim_customer.ledger_group_name column
- `SCHEMA_FOR_AI.md` - Updated for AI context with ledger group information
- `README.md` - Added mention of ledger masters in quick start
- `Makefile.example` - Example workflow integration

## How It Works

### Data Flow

```
Tally ERP
    ↓
ledgers.xml.j2 (HTTP Request)
    ↓
Tally XML Response (LEDGER and GROUP elements)
    ↓
ledgers_parser.py (Parse XML)
    ↓
ledger_masters.py (ETL Script)
    ├──→ dim_ledger_group (Upsert groups)
    └──→ dim_customer (Update ledger_group_name)
```

### Customer Assignment Logic

1. Fetch all ledgers from Tally with their parent group names
2. Create mapping: `ledger_name → parent_group_name`
3. Update `dim_customer.ledger_group_name` where:
   - `dim_customer.customer_id` matches `ledger_name`, OR
   - `dim_customer.name` matches `ledger_name`

### Example Hierarchy

```
Sundry Debtors (root group)
  ├── North Zone Debtors
  │   ├── Delhi Customers
  │   │   ├── Acme Corp (customer)
  │   │   └── Beta Ltd (customer)
  │   └── Punjab Customers
  │       └── Gamma Inc (customer)
  └── South Zone Debtors
      ├── Mumbai Customers
      │   └── Delta Enterprises (customer)
      └── Bangalore Customers
          └── Epsilon Ltd (customer)
```

## Usage Examples

### Basic Usage

```bash
# Fetch and load ledger masters from Tally
python -m agent.ledger_masters --from-tally

# Test with dry-run first
python -m agent.ledger_masters --from-tally --dry-run --preview 50
```

### Querying Ledger Groups

```sql
-- Sales by Ledger Group
SELECT 
    dc.ledger_group_name,
    COUNT(DISTINCT dc.customer_id) AS customer_count,
    COUNT(DISTINCT fi.invoice_id) AS invoice_count,
    SUM(fi.total) AS total_sales
FROM fact_invoice fi
JOIN dim_customer dc ON dc.customer_id = fi.customer_id
WHERE fi.date >= '2025-01-01'
  AND dc.ledger_group_name IS NOT NULL
GROUP BY dc.ledger_group_name
ORDER BY total_sales DESC;

-- Customers in Specific Group
SELECT 
    dc.name AS customer,
    dc.gstin,
    dc.city,
    COUNT(DISTINCT fi.invoice_id) AS invoice_count,
    SUM(fi.total) AS total_sales
FROM dim_customer dc
LEFT JOIN fact_invoice fi ON fi.customer_id = dc.customer_id
WHERE dc.ledger_group_name = 'North Zone Debtors'
  AND fi.date >= '2025-01-01'
GROUP BY dc.name, dc.gstin, dc.city
ORDER BY total_sales DESC;
```

### Workflow Integration

**Recommended: Periodic Refresh (Weekly/Monthly)**

```bash
# Weekly master data sync
python -m agent.stock_masters --from-tally
python -m agent.ledger_masters --from-tally

# Daily transaction sync
python -m agent.run
```

**Using Makefile:**

```makefile
sync-masters:
    python -m agent.stock_masters --from-tally
    python -m agent.ledger_masters --from-tally

sync-transactions:
    python -m agent.run
```

**Using Cron:**

```bash
# Weekly master sync (Sunday 2 AM)
0 2 * * 0 cd /path/to/intelayer && make sync-masters

# Daily transaction sync (every day at 3 AM)
0 3 * * * cd /path/to/intelayer && python -m agent.run
```

## Files Created/Modified

### New Files (4)

1. `warehouse/migrations/0007_ledger_masters.sql` - Database migration
2. `adapters/tally_http/requests/ledgers.xml.j2` - Tally XML request template
3. `adapters/tally_http/ledgers_parser.py` - Ledger XML parser
4. `agent/ledger_masters.py` - ETL script

### Documentation Files (3)

1. `LEDGER_MASTER_USAGE.md` - Usage guide
2. `LEDGER_MASTERS_IMPLEMENTATION.md` - This file
3. `Makefile.example` - Example workflow integration

### Updated Files (4)

1. `DATABASE_SCHEMA.md` - Added dim_ledger_group and dim_customer.ledger_group_name
2. `SCHEMA_FOR_AI.md` - Updated for AI context
3. `README.md` - Added ledger masters to quick start
4. `.gitignore` - No changes needed (already ignores *.xml)

## Testing

### Test the Implementation

```bash
# 1. Test with dry-run first
python -m agent.ledger_masters --from-tally --dry-run --preview 50

# 2. If successful, run for real
python -m agent.ledger_masters --from-tally

# 3. Verify in database
psql $DB_URL -c "SELECT COUNT(*) FROM dim_ledger_group;"
psql $DB_URL -c "SELECT COUNT(*) FROM dim_customer WHERE ledger_group_name IS NOT NULL;"

# 4. Check hierarchy
psql $DB_URL -c "
SELECT 
    g.name AS root, 
    c.name AS child 
FROM dim_ledger_group g 
LEFT JOIN dim_ledger_group c ON c.parent_name = g.name 
WHERE g.parent_name IS NULL 
LIMIT 20;
"
```

## Troubleshooting

### No Ledger Groups Found

**Symptoms:** Script reports "0 groups" after running

**Solutions:**
1. Check if Tally XML response contains `<LEDGER>` or `<GROUP>` elements
2. Verify Tally company has ledger groups configured
3. Try different account type in `ledgers.xml.j2`:
   ```xml
   <AccountType>Ledgers</AccountType>
   ```
   Or:
   ```xml
   <AccountType>Groups</AccountType>
   ```

### Customers Not Getting Assigned

**Symptoms:** `dim_customer.ledger_group_name` is NULL for all customers

**Solutions:**
1. Ensure customers exist in `dim_customer` first (run `python -m agent.run`)
2. Verify customer names in `dim_customer` match ledger names in Tally
3. Check if ledgers have `PARENT` tags in XML response
4. Run with `--preview` to see sample ledger → group mappings

### Duplicate Group Names

**Symptoms:** "duplicate key value violates unique constraint" error

**Solutions:**
1. Groups are identified by name (fallback when GUID is missing)
2. If Tally has duplicate group names, the script will update the first match
3. Ensure Tally data is clean or modify parser to handle duplicates

## Benefits

1. **Customer Segmentation**: Group customers by ledger groups for better reporting
2. **Hierarchical Reporting**: Support multi-level hierarchy (e.g., Sundry Debtors → North Zone → Delhi)
3. **Tally Integration**: Automatically sync ledger group structure from Tally
4. **Flexible Workflow**: Can run separately from transaction sync (weekly vs daily)
5. **Consistent Pattern**: Follows same pattern as stock masters for maintainability

## Next Steps

1. **Test the Implementation**: Run `python -m agent.ledger_masters --from-tally --dry-run`
2. **Load Data**: Run `python -m agent.ledger_masters --from-tally`
3. **Verify**: Check `dim_ledger_group` and `dim_customer.ledger_group_name` in database
4. **Set Up Workflow**: Add to Makefile or cron for periodic refresh
5. **Create Reports**: Build Metabase dashboards using ledger group segmentation

## Related Documentation

- `LEDGER_MASTER_USAGE.md` - Comprehensive usage guide
- `DATABASE_SCHEMA.md` - Complete schema documentation
- `STOCK_MASTER_USAGE.md` - Similar pattern for stock masters
- `README.md` - Quick start guide

