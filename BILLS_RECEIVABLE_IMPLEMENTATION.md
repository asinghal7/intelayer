# Bills Receivable Implementation

## Overview

Implemented a complete AR/AP pipeline for bill-wise receivables tracking. The pipeline fetches data directly from Tally's **Outstanding Receivables** report, which is more accurate than reconstructing from transactions.

## Problem Solved

### Original Issue
1. **Incomplete opening balances**: Only 144 bill-wise opening records vs. 2,791 bills with payments
2. **Orphaned payments**: Payments against bills created before the date range had no corresponding invoice creation records
3. **Missing bills**: "Apollo Communication, Ramnagar" and many others had no opening balances despite having payments

### Root Cause
Reconstructing bill-wise outstanding from transactions is complex because:
- Bills can be created in any period
- Payments can be made in later periods
- Opening balances may not include all bill-wise details
- Need to track both invoice creation and all subsequent payments

## Solution

### Approach: Transaction-Based with Corrected Sign Handling

The pipeline reconstructs bill-wise outstanding amounts from transaction data (vouchers with bill allocations) with proper sign handling:

**Key Fixes:**
1. ✅ Opening balances: Only include debit balances (`opening_balance < 0`) as receivables
2. ✅ New bills: Convert negative amounts to positive using `abs()`
3. ✅ Payments: Convert amounts to positive using `abs()` for adjustments
4. ✅ Pending calculation: `pending = original - adjusted` (both positive)
5. ✅ Batched processing (30-day chunks) to avoid Tally crashes

**Limitations:**
- Bills created before the date range will show as orphaned payments (original_amount = 0)
- For complete data, ensure opening balances are populated via `pull-opening-bills`

## Architecture

### Tables

1. **`fact_bills_receivable`** - Bill-wise outstanding receivables (primary table)
   - `ledger` - Ledger name (party)
   - `bill_name` - Bill/invoice reference
   - `bill_date` - Invoice date
   - `due_date` - Due date (calculated from credit period)
   - `original_amount` - Original bill amount
   - `adjusted_amount` - Total payments/adjustments
   - `pending_amount` - Outstanding amount
   - `billtype` - Bill type
   - `is_advance` - Whether it's an advance
   - `last_seen_at` - Last updated timestamp

2. **`view_billwise_outstanding`** - Report view with aging analysis
   - All fields from `fact_bills_receivable`
   - `days_overdue` - Days since due date
   - `aging_bucket` - Aging classification (0-30, 31-60, 61-90, 90+)

3. **`view_ledger_outstanding_summary`** - Ledger-wise summary
   - Total bills per ledger
   - Total pending amounts
   - Aging breakdown by bucket

### Components

1. **XML Template**: `adapters/tally_http/ar_ap/requests/outstanding_receivables.xml.j2`
   - Fetches Outstanding Receivables report from Tally
   - Uses `EXPLODEFLAG=Yes` to get bill-wise details

2. **Parser**: `adapters/tally_http/ar_ap/parser.py::parse_outstanding_receivables()`
   - Extracts ledger, bill_name, amounts, dates from XML
   - Handles sign conventions (negative for debtors → positive for reporting)

3. **Adapter**: `adapters/tally_http/ar_ap/adapter.py::fetch_outstanding_receivables_xml()`
   - Wrapper to fetch Outstanding Receivables report
   - Takes `as_of_date` parameter for snapshot

4. **Loader**: `agent/etl_ar_ap/loader.py`
   - `load_stg_trn_bill()` - Loads transaction bill allocations into staging
   - `upsert_fact_bills_receivable()` - Transforms staging data and calculates outstanding
   - Complex SQL to combine opening balances with transaction bills
   - Handles sign conventions (debit/credit)
   - Idempotent (upsert on conflict)

5. **Entrypoint**: `run_bills_receivable.py`
   - Main script to run the pipeline
   - Processes date range in batches (default 30 days)
   - Logs progress
   - Environment variables: `BATCH_DAYS` to adjust batch size

## Usage

### Run the Pipeline

```bash
# Load bills receivable from transactions
./tasks_ar_ap.sh pull-bills-receivable
```

### Manual Run

```bash
# Set environment variables
export TALLY_URL=http://localhost:9000
export TALLY_COMPANY="Your Company"
export DB_URL="postgresql://user:pass@localhost/db"

# Run pipeline
python -m run_bills_receivable_from_outstanding
```

### Query the Data

```sql
-- View all outstanding receivables
SELECT * FROM view_billwise_outstanding;

-- Ledger-wise summary with aging
SELECT * FROM view_ledger_outstanding_summary;

-- Outstanding by aging bucket
SELECT 
    aging_bucket,
    COUNT(*) as bill_count,
    SUM(pending_amount) as total_pending
FROM view_billwise_outstanding
GROUP BY aging_bucket
ORDER BY 
    CASE aging_bucket
        WHEN 'Not Due' THEN 1
        WHEN '0-30 Days' THEN 2
        WHEN '31-60 Days' THEN 3
        WHEN '61-90 Days' THEN 4
        WHEN '90+ Days' THEN 5
        ELSE 6
    END;

-- Specific ledger outstanding
SELECT *
FROM view_billwise_outstanding
WHERE ledger = 'Apollo Communication, Ramnagar'
ORDER BY bill_date;
```

## Data Flow

```
Tally ERP
    ↓
[Daybook XML with Bill Allocations - Batched]
    ↓
parse_trn_bill_allocations()
    ↓
load_stg_trn_bill() → stg_trn_bill
    ↓
upsert_fact_bills_receivable()
  (combines opening balances + transactions)
    ↓
fact_bills_receivable
    ↓
view_billwise_outstanding
view_ledger_outstanding_summary
```

## Validation

### Check Data Quality

```bash
# Run debug script
python debug_bills_receivable.py
```

**Expected output:**
- Bills with both New Ref and Agst Ref should have correct pending amounts
- No mismatches between expected and actual pending amounts
- Total pending amount should match Tally's Outstanding Receivables total

### Verify in Metabase

1. Create a question using `view_billwise_outstanding`
2. Filter by `pending_amount > 0`
3. Compare totals with Tally's Outstanding Receivables report
4. Verify specific ledgers match Tally's bill-wise details

## Sign Handling Logic

Understanding Tally's accounting conventions for receivables:

### Opening Balances
- **Negative** opening_balance = Debit balance = Customer owes us = Receivable ✅
- **Positive** opening_balance = Credit balance = We owe customer = Advance (excluded)

### Transactions
- **"New Ref"** (invoice creation): Amount is negative in Tally → Convert to positive for reporting
- **"Agst Ref"** (payment/adjustment): Amount is positive in Tally → Sum as positive adjustments

### Calculation
```sql
original_amount = abs(New Ref amounts + negative opening balances)
adjusted_amount = abs(sum of Agst Ref amounts)
pending_amount = original_amount - adjusted_amount
```

This ensures all amounts are positive for reporting, with pending_amount showing the true outstanding receivable.

## Files Created/Modified

### New Files
- `warehouse/migrations/0009_bills_receivable.sql` - DDL for staging and fact tables
- `warehouse/migrations/0010_view_billwise_outstanding.sql` - Report views
- `run_bills_receivable.py` - Main pipeline entrypoint
- `BILLS_RECEIVABLE_IMPLEMENTATION.md` - Documentation
- `debug_bills_receivable.py` - Diagnostic script

### Modified Files
- `adapters/tally_http/ar_ap/parser.py` - Added `parse_trn_bill_allocations()`
- `adapters/tally_http/ar_ap/adapter.py` - Added `fetch_vouchers_with_bills_xml()`
- `agent/etl_ar_ap/loader.py` - Fixed sign handling in `upsert_fact_bills_receivable()`
- `tasks_ar_ap.sh` - Added `pull-bills-receivable` and `ddl-views` commands
- `adapters/tally_http/client.py` - Increased timeout to 300 seconds

## Next Steps

1. **Run the pipeline**: `./tasks_ar_ap.sh pull-bills-receivable`
2. **Verify data**: Compare with Tally's Outstanding Receivables report
3. **Create Metabase dashboards**: Use `view_billwise_outstanding` and `view_ledger_outstanding_summary`
4. **Schedule regular runs**: Add to cron/scheduler to refresh daily

## Metabase Dashboard Ideas

### Bill-wise Outstanding Report
- Table showing ledger, bill_name, bill_date, due_date, pending_amount, days_overdue
- Filter by ledger, aging bucket, date range
- Sort by pending_amount desc

### Aging Analysis
- Bar chart showing pending amount by aging bucket
- Pie chart showing % of total by bucket
- Table showing top 10 overdue customers

### Ledger Summary
- Table from `view_ledger_outstanding_summary`
- Total pending per ledger
- Aging breakdown per ledger
- Filter by minimum pending amount

### Trends
- Line chart showing total outstanding over time (requires historical snapshots)
- Bar chart showing new bills vs. payments per month

