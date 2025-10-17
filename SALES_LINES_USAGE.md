# Sales Lines from Voucher Register - Usage Guide

## Overview

The Sales Lines ETL extracts item-level line details from Tally's Voucher Register and persists them into `fact_invoice_line` table. This enables answering "who bought which SKU" with complete line-item details including quantities, rates, and tax allocations.

## Architecture

### Data Flow
```
Tally Voucher Register (DayBook XML)
    ↓
Parser (extracts inventory entries)
    ↓
Staging Tables (stg_vreg_header, stg_vreg_line)
    ↓
fact_invoice (headers with ON CONFLICT)
    ↓
fact_invoice_line (line items with tax allocation)
```

### Key Components

1. **Parser Enhancement** (`adapters/tally_http/parser.py`)
   - Added `_parse_inventory_entries()` function
   - Extracts: `StockItemName`, `BilledQty`, `Rate`, `Amount`, `Discount`
   - Returns list of inventory entry dicts per voucher

2. **ETL Module** (`agent/sales_lines_from_vreg.py`)
   - Fetches vouchers using existing Voucher Register logic
   - Stages headers and lines
   - Upserts headers to `fact_invoice`
   - Inserts line items with proportional tax allocation
   - Supports batching for large date ranges

3. **Database Schema** (`warehouse/migrations/0006_fact_invoice_line.sql`)
   - `fact_invoice_line` table with line-level details
   - Staging tables for temporary data
   - Proper indexes and foreign keys

## Usage

### Basic Commands

#### 1. Process Last 7 Days
```bash
python agent/run.py sales-lines-from-vreg --lookback-days 7
```

#### 2. Process Specific Date Range
```bash
python agent/run.py sales-lines-from-vreg --from 2025-04-01 --to 2025-10-15
```

#### 3. Dry Run with Preview
```bash
python agent/run.py sales-lines-from-vreg --lookback-days 7 --dry-run --preview 20
```

#### 4. Full Financial Year with Preview
```bash
python agent/run.py sales-lines-from-vreg --from 2024-04-01 --to 2025-03-31 --preview 50
```

### Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `--lookback-days N` | Process last N days | `--lookback-days 7` |
| `--from YYYY-MM-DD` | Start date | `--from 2025-04-01` |
| `--to YYYY-MM-DD` | End date | `--to 2025-10-15` |
| `--dry-run` | Preview without DB writes | `--dry-run` |
| `--preview N` | Show top N lines | `--preview 20` |

### Batching

The ETL automatically batches large date ranges:
- **≤15 days**: Single batch processing
- **>15 days**: Automatic 15-day batches with progress logging
- **Pause**: 1-second pause between batches

Example output:
```
Processing 45 days in batches of 15: 2025-09-01 to 2025-10-15
🔄 Processing batch 1: 2025-09-01 to 2025-09-15
✅ Batch 1 completed: 189 headers, 139 lines
🔄 Processing batch 2: 2025-09-16 to 2025-09-30
✅ Batch 2 completed: 343 headers, 444 lines
🔄 Processing batch 3: 2025-10-01 to 2025-10-15
✅ Batch 3 completed: 303 headers, 365 lines
🎉 All batches completed! Total: 835 headers, 930 lines
```

## Data Model

### fact_invoice_line Schema

| Column | Type | Description |
|--------|------|-------------|
| `invoice_line_id` | bigserial | Primary key (auto-increment) |
| `invoice_id` | text | Foreign key to fact_invoice |
| `sku_id` | text | Foreign key to dim_item (nullable) |
| `sku_name` | text | Item name as seen on voucher |
| `qty` | numeric(14,3) | Quantity |
| `uom` | text | Unit of measure (Nos, Kg, etc.) |
| `rate` | numeric(14,2) | Rate per unit |
| `discount` | numeric(14,2) | Line discount (if any) |
| `line_basic` | numeric(14,2) | Pre-tax amount |
| `line_tax` | numeric(14,2) | Allocated tax |
| `line_total` | numeric(14,2) | Total (basic + tax) |
| `created_at` | timestamptz | Timestamp |

### Tax Allocation Logic

Tax is allocated proportionally to each line based on:
```sql
line_tax = (line_basic / sum_line_basic) * voucher_tax
line_total = line_basic + line_tax
```

## Querying the Data

### Who Bought Which SKU
```sql
select 
  fi.date,
  fi.voucher_key as invoice_no,
  dc.name as customer,
  fil.sku_name,
  fil.qty,
  fil.uom,
  fil.rate,
  fil.line_basic,
  fil.line_tax,
  fil.line_total
from fact_invoice fi
join fact_invoice_line fil on fil.invoice_id = fi.invoice_id
left join dim_customer dc on dc.customer_id = fi.customer_id
where fi.date between '2025-09-01' and '2025-09-30'
order by fi.date desc, fi.voucher_key;
```

### Top Selling Items
```sql
select 
  fil.sku_name,
  sum(fil.qty) as total_qty,
  sum(fil.line_total) as total_revenue,
  count(distinct fil.invoice_id) as invoice_count
from fact_invoice_line fil
join fact_invoice fi on fi.invoice_id = fil.invoice_id
where fi.date between '2025-09-01' and '2025-09-30'
group by fil.sku_name
order by total_revenue desc
limit 20;
```

### Customer Purchase Analysis
```sql
select 
  dc.name as customer,
  count(distinct fi.invoice_id) as invoice_count,
  count(fil.invoice_line_id) as line_count,
  sum(fil.line_total) as total_amount
from fact_invoice fi
join fact_invoice_line fil on fil.invoice_id = fi.invoice_id
left join dim_customer dc on dc.customer_id = fi.customer_id
where fi.date between '2025-09-01' and '2025-09-30'
group by dc.name
order by total_amount desc;
```

## Expected Behavior

### Line Count Discrepancy

A small percentage of lines may not be inserted due to:

1. **Challan/Delivery Vouchers**: Don't have invoice pricing (rate/qty)
2. **Empty Fields**: Missing `BILLEDQTY` or `RATE` in XML
3. **Non-Invoice Vouchers**: Vouchers without proper inventory entries

This is **expected behavior** - the ETL correctly filters out non-invoice line items.

Example:
- Staged: 953 lines
- Inserted: 930 lines (97.6%)
- Dropped: 23 lines (2.4%) ← Challans/non-invoices

### Duplicate Handling

- **Headers**: `ON CONFLICT (invoice_id) DO UPDATE` - updates existing
- **Lines**: Delete existing lines for invoice, then insert new
- **Idempotent**: Running multiple times produces same result

## Troubleshooting

### Issue: Only Last Batch Data Persists

**Symptom**: Final verification shows only last batch's line count

**Cause**: Migration running on every batch (old bug, now fixed)

**Solution**: Migration now runs once at start, not per batch

### Issue: "set-returning functions are not allowed in WHERE"

**Symptom**: PostgreSQL error during debugging query

**Cause**: Using `regexp_matches()` directly in WHERE clause

**Solution**: Wrap in CTE (already fixed in code)

### Issue: Low Line Count

**Symptom**: Fewer lines than expected

**Possible Causes**:
1. Challan vouchers (no pricing)
2. Missing `BILLEDQTY` or `RATE` fields
3. Join failures (GUID mismatches)

**Debug**: Run with `--preview` to see sample data

## Performance

### Benchmarks

- **Small range (7 days)**: ~5-10 seconds
- **Medium range (45 days)**: ~15-30 seconds
- **Full FY (365 days)**: ~2-5 minutes (batched)

### Optimization Tips

1. **Use batching**: Automatic for ranges >15 days
2. **Run during off-hours**: For large backfills
3. **Incremental updates**: Use `--lookback-days` for daily runs
4. **Preview first**: Use `--dry-run --preview` before large runs

## Integration with Existing ETL

### Current Flow (agent/run.py)

The existing `run.py` processes:
1. **Invoices**: All vouchers → `fact_invoice`
2. **Receipts**: Receipt vouchers → `fact_receipt`

### New Flow (sales-lines-from-vreg)

Adds line-level details:
1. **Headers**: Same as existing (reuses logic)
2. **Lines**: New `fact_invoice_line` table

### Running Together

```bash
# 1. Run existing ETL (headers)
python agent/run.py

# 2. Run sales lines ETL (lines)
python agent/run.py sales-lines-from-vreg --lookback-days 7
```

Or combine in a script:
```bash
#!/bin/bash
python agent/run.py && \
python agent/run.py sales-lines-from-vreg --lookback-days 7
```

## Maintenance

### Regular Operations

**Daily**: Process yesterday's data
```bash
python agent/run.py sales-lines-from-vreg --lookback-days 1
```

**Weekly**: Backfill last 7 days
```bash
python agent/run.py sales-lines-from-vreg --lookback-days 7
```

**Monthly**: Full month
```bash
python agent/run.py sales-lines-from-vreg --from 2025-09-01 --to 2025-09-30
```

### Monitoring

Check line counts:
```sql
select 
  date_trunc('day', created_at) as date,
  count(*) as line_count
from fact_invoice_line
group by date_trunc('day', created_at)
order by date desc
limit 7;
```

Check for missing data:
```sql
select 
  fi.invoice_id,
  fi.voucher_key,
  fi.date,
  count(fil.invoice_line_id) as line_count
from fact_invoice fi
left join fact_invoice_line fil on fil.invoice_id = fi.invoice_id
where fi.date >= current_date - interval '7 days'
  and fil.invoice_line_id is null
group by fi.invoice_id, fi.voucher_key, fi.date;
```

## Best Practices

1. **Always preview first**: Use `--dry-run --preview` for new date ranges
2. **Batch large ranges**: Automatic for >15 days
3. **Monitor line counts**: Check for unexpected drops
4. **Run incrementally**: Use `--lookback-days` for regular updates
5. **Handle challans separately**: They don't have pricing data

## Related Documentation

- `instructions.md` - Original implementation plan
- `STOCK_MASTER_USAGE.md` - Stock masters ETL
- `BACKFILL_GUIDE.md` - Backfill procedures
- `COMPLETE_FIX_SUMMARY.md` - Historical fixes

## Support

For issues or questions:
1. Check logs for error messages
2. Run with `--preview` to see sample data
3. Check database for line count discrepancies
4. Review Tally XML structure for missing fields

