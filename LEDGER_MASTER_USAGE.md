# Ledger Master ETL Usage Guide

## Overview

The Ledger Master ETL loads ledger group hierarchy and customer ledger group assignments from Tally. This enables customer segmentation and reporting by ledger groups (e.g., "Sundry Debtors", "North Zone Debtors", etc.).

## What Gets Loaded

### 1. Ledger Groups (`dim_ledger_group`)

Hierarchical grouping of ledgers/customers in Tally:

```
Sundry Debtors (root)
  ├── North Zone Debtors
  │   ├── Delhi Customers
  │   └── Punjab Customers
  └── South Zone Debtors
      ├── Mumbai Customers
      └── Bangalore Customers
```

### 2. Customer Ledger Group Assignment (`dim_customer.ledger_group_name`)

Each customer is assigned to their parent ledger group:

```sql
SELECT name, ledger_group_name 
FROM dim_customer 
WHERE ledger_group_name IS NOT NULL;

-- Example output:
-- Acme Corp    | Delhi Customers
-- Beta Ltd     | Mumbai Customers
-- Gamma Inc    | Punjab Customers
```

## Usage

### Fetch from Tally (Recommended)

```bash
# Fetch and load ledger masters from Tally
python -m agent.ledger_masters --from-tally
```

This will:
1. Fetch ledger data from Tally via HTTP
2. Parse ledger groups and hierarchy
3. Upsert into `dim_ledger_group`
4. Update `dim_customer.ledger_group_name` based on ledger assignments

### Test with File (Dry Run)

```bash
# Export ledgers from Tally manually, then test
python -m agent.ledger_masters --from-file ledgers.xml --dry-run --preview 50
```

### Load from File

```bash
# Load from pre-exported XML file
python -m agent.ledger_masters --from-file ledgers.xml
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `--from-tally` | Fetch data from Tally via HTTP |
| `--from-file <path>` | Load from local XML file |
| `--dry-run` | Preview without writing to database |
| `--preview N` | Show N sample records (default: 50) |

## Database Schema

### dim_ledger_group

| Column | Type | Description |
|--------|------|-------------|
| `ledger_group_id` | bigserial | Auto-increment ID |
| `guid` | text | Tally GUID (unique) |
| `name` | text | Group name (unique) |
| `parent_name` | text | Parent group name (NULL for roots) |
| `alter_id` | bigint | Tally alteration ID |
| `updated_at` | timestamptz | Last update timestamp |

### dim_customer (new column)

| Column | Type | Description |
|--------|------|-------------|
| `ledger_group_name` | text | Ledger group this customer belongs to |

## Workflow Integration

### Recommended: Periodic Refresh

Ledger masters change less frequently than transactions. Run periodically (weekly/monthly):

```bash
# Weekly master data sync
python -m agent.stock_masters --from-tally
python -m agent.ledger_masters --from-tally

# Daily transaction sync
python -m agent.run
```

### Using Makefile

Create a `Makefile` in the project root:

```makefile
.PHONY: sync-masters sync-transactions

# Run weekly/monthly
sync-masters:
	python -m agent.stock_masters --from-tally
	python -m agent.ledger_masters --from-tally

# Run daily
sync-transactions:
	python -m agent.run

# Run everything
sync-all: sync-masters sync-transactions
```

Then run:
```bash
make sync-masters  # Weekly
make sync-transactions  # Daily
```

### Using Cron (Linux/Mac)

Add to crontab for automated runs:

```bash
# Edit crontab
crontab -e

# Add lines:
# Weekly master sync (Sunday 2 AM)
0 2 * * 0 cd /path/to/intelayer && make sync-masters

# Daily transaction sync (every day at 3 AM)
0 3 * * * cd /path/to/intelayer && python -m agent.run
```

## Querying Ledger Groups

### Customers by Ledger Group

```sql
SELECT 
    lg.name AS ledger_group,
    COUNT(DISTINCT dc.customer_id) AS customer_count,
    SUM(fi.total) AS total_sales
FROM dim_ledger_group lg
LEFT JOIN dim_customer dc ON dc.ledger_group_name = lg.name
LEFT JOIN fact_invoice fi ON fi.customer_id = dc.customer_id
WHERE fi.date >= '2025-01-01'
GROUP BY lg.name
ORDER BY total_sales DESC;
```

### Ledger Group Hierarchy

```sql
WITH RECURSIVE group_hierarchy AS (
    -- Root groups
    SELECT 
        name,
        parent_name,
        0 AS depth,
        name AS path
    FROM dim_ledger_group
    WHERE parent_name IS NULL
    
    UNION ALL
    
    -- Child groups
    SELECT 
        lg.name,
        lg.parent_name,
        gh.depth + 1,
        gh.path || ' > ' || lg.name
    FROM dim_ledger_group lg
    JOIN group_hierarchy gh ON lg.parent_name = gh.name
    WHERE gh.depth < 10  -- safety limit
)
SELECT 
    LPAD('', depth * 2, ' ') || name AS group_name,
    path
FROM group_hierarchy
ORDER BY path;
```

### Customers in Specific Group

```sql
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

## Troubleshooting

### No Ledger Groups Found

**Issue**: Script reports "0 groups" after running.

**Solutions**:
1. Check if Tally XML response contains `<LEDGER>` or `<GROUP>` elements
2. Verify Tally company has ledger groups configured
3. Try fetching with different account type in `ledgers.xml.j2`:
   ```xml
   <AccountType>Ledgers</AccountType>
   ```
   Or try:
   ```xml
   <AccountType>Groups</AccountType>
   ```

### Customers Not Getting Assigned

**Issue**: `dim_customer.ledger_group_name` is NULL for all customers.

**Solutions**:
1. Ensure customers exist in `dim_customer` first (run `python -m agent.run`)
2. Verify customer names in `dim_customer` match ledger names in Tally
3. Check if ledgers have `PARENT` tags in XML response
4. Run with `--preview` to see sample ledger → group mappings

### Duplicate Group Names

**Issue**: "duplicate key value violates unique constraint" on `dim_ledger_group.name`.

**Solutions**:
1. Groups are identified by name (fallback when GUID is missing)
2. If Tally has duplicate group names, the script will update the first match
3. Ensure Tally data is clean or modify parser to handle duplicates

## Migration

The ledger master functionality is added via migration `0007_ledger_masters.sql`.

To apply:
```bash
# Migration runs automatically when ledger_masters.py is executed
python -m agent.ledger_masters --from-tally
```

Or manually:
```bash
psql -d your_database -f warehouse/migrations/0007_ledger_masters.sql
```

## Related Documentation

- `STOCK_MASTER_USAGE.md` - Stock masters ETL guide
- `DATABASE_SCHEMA.md` - Complete database schema
- `BACKFILL_GUIDE.md` - Historical data backfill
- `SETUP_INSTRUCTIONS.md` - Initial setup

## Best Practices

1. **Run ledger masters periodically** (not with every transaction sync)
2. **Test with `--dry-run` first** before loading production data
3. **Save Tally responses** for debugging (script auto-saves to `tally_ledgers_response.xml`)
4. **Monitor customer assignments** - check how many customers have `ledger_group_name` set
5. **Update after customer changes** - if you add new customers in Tally, re-run ledger masters

## Example Output

```
2025-10-16 10:30:00 | INFO     | Loading XML from file: ledgers.xml
2025-10-16 10:30:01 | INFO     | Parsing ledgers XML...
2025-10-16 10:30:01 | INFO     | Parsed: 15 groups, 234 ledgers
2025-10-16 10:30:01 | INFO     | Found 3 root groups:
2025-10-16 10:30:01 | INFO     |   - Sundry Debtors
2025-10-16 10:30:01 | INFO     |   - Bank Accounts
2025-10-16 10:30:01 | INFO     |   - Cash Accounts
2025-10-16 10:30:02 | INFO     | Ensuring schema exists...
2025-10-16 10:30:02 | SUCCESS  | Schema validated/created
2025-10-16 10:30:02 | INFO     | Upserting ledger groups...
2025-10-16 10:30:02 | SUCCESS  | Groups: 15 inserted, 0 updated
2025-10-16 10:30:02 | INFO     | Updating customer ledger group assignments...
2025-10-16 10:30:02 | SUCCESS  | Customers updated: 234

=== Preview ===

Totals:
  Ledger Groups: 15
  Customers with Ledger Group: 234

Ledger Group Hierarchy (first 20):
  [Bank Accounts]
  [Cash Accounts]
  [Sundry Debtors]
    - North Zone Debtors
    - South Zone Debtors
    - West Zone Debtors

Sample Customers with Ledger Groups (first 20):
  [North Zone Debtors]
    - Acme Distributors
    - Beta Corporation
    - Gamma Industries
  [South Zone Debtors]
    - Delta Enterprises
    - Epsilon Ltd

=== Developer Checklist ===
✓ Ledger groups loaded: 15
✓ Customers with ledger group: 234
```

