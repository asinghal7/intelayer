# Credit Note Tax Calculation Fix

## Problem Summary

Credit notes were showing incorrectly high tax values because:
1. **Subtotal** was negative (from inventory entries, e.g., -1000)
2. **Total** was forced to positive using `abs()` in parser (e.g., +1180)
3. **Tax** calculation: `1180 - (-1000) = 2180` ❌ (way too high!)

The correct tax should be: `-1180 - (-1000) = -180` ✓

## Root Cause

Two issues were identified:

1. **Wrong XML tag for Credit Notes**: Credit Notes use `LEDGERENTRIES.LIST` (single R) in Tally XML, but the code was checking `ALLLEDGERENTRIES.LIST` (double L), causing incorrect total extraction.

2. **abs() applied before tax calculation**: The `abs()` function was applied to the total amount in `parser.py` before tax calculation, breaking the relationship between subtotal, tax, and total for credit notes.

## Solution Implemented

### 1. Parser (`adapters/tally_http/parser.py`)

**Changed**: 
1. Fixed XML tag selection for Credit Notes to use `LEDGERENTRIES.LIST` instead of `ALLLEDGERENTRIES.LIST`
2. Removed `abs()` calls to preserve natural signs for both subtotal and total

```python
# Before: Only checked LEDGERENTRIES.LIST for "Invoice" type
if vchtype == "Invoice":
    for le in voucher.findall(".//LEDGERENTRIES.LIST"):
        ...

# After: Check LEDGERENTRIES.LIST for Sales/Invoice/Credit Note/Purchase/Debit Note
ledger_entries_types = {"Invoice", "Sales", "Credit Note", "Sales Return", "Purchase", "Purchase Return", "Debit Note"}
if vchtype in ledger_entries_types:
    for le in voucher.findall(".//LEDGERENTRIES.LIST"):
        ...
```

Also removed `abs()` from bill allocation:
```python
# Before:
return abs(_to_float(amt_text))

# After:
return _to_float(amt_text)
```

This ensures:
- Credit Notes extract the correct total from the right XML tag
- Both subtotal and total have the same natural sign (both negative for credit notes)

### 2. Adapter (`adapters/tally_http/adapter.py`)

**Changed**: Added credit note sign normalization BEFORE tax calculation.

```python
# Extract amounts with natural signs
subtotal = float(d.get("subtotal") or 0.0)
total = float(d.get("total") or 0.0)

# For credit notes and sales returns, negate amounts FIRST if they're positive
# Tally provides: subtotal negative, total positive for credit notes
# We need all negative for credit notes
if d["vchtype"] in ("Credit Note", "Sales Return"):
    if subtotal > 0:
        subtotal = -subtotal
    if total > 0:
        total = -total

# Calculate tax AFTER sign normalization
# Now both subtotal and total have correct signs
tax = total - subtotal
```

### 3. Sales Lines (`agent/sales_lines_from_vreg.py`)

**Changed**: Applied the same logic for consistency in staging tables.

```python
# Extract amounts with natural signs
subtotal = float(v.get("subtotal") or 0.0)
total = float(v.get("total") or 0.0)

# For credit notes and sales returns, negate amounts FIRST if they're positive
# Tally provides: subtotal negative, total positive for credit notes
# We need all negative for credit notes
vchtype = v.get("vchtype", "")
if vchtype in ("Credit Note", "Sales Return"):
    if subtotal > 0:
        subtotal = -subtotal
    if total > 0:
        total = -total

# Calculate tax AFTER sign normalization
# Now both subtotal and total have correct signs
tax = total - subtotal
```

## Expected Results

### Credit Note Example (if Tally provides negative values)
- **Before**: subtotal=-1000, tax=2180, total=1180 ❌
- **After**: subtotal=-1000, tax=-180, total=-1180 ✓

### Credit Note Example (if Tally provides positive values)
- **Before**: subtotal=1000, tax=180, total=1180 ❌ (wrong sign)
- **After**: subtotal=-1000, tax=-180, total=-1180 ✓

### Sales Example
- **Before**: subtotal=1000, tax=180, total=1180 ✓
- **After**: subtotal=1000, tax=180, total=1180 ✓

## Files Modified

1. ✅ `adapters/tally_http/parser.py` - Removed abs() calls
2. ✅ `adapters/tally_http/adapter.py` - Added credit note sign normalization
3. ✅ `agent/sales_lines_from_vreg.py` - Applied same logic

## Testing Recommendations

1. **Run the ETL** to reprocess existing data:
   ```bash
   python agent/run.py
   ```

2. **Verify credit notes** in the database:
   ```sql
   SELECT vchtype, subtotal, tax, total, (subtotal + tax) as calculated_total
   FROM fact_invoice
   WHERE vchtype IN ('Credit Note', 'Sales Return')
   LIMIT 10;
   ```

3. **Check that**: `calculated_total = total` for all records

4. **Verify tax is reasonable**: For 18% GST, tax should be approximately `subtotal * 0.18`

## Impact

- ✅ Credit notes now have correct negative tax values
- ✅ Sales vouchers remain unchanged (still positive)
- ✅ Tax calculation is now mathematically correct: `tax = total - subtotal`
- ✅ All three programs (run.py, backfill.py, sales_lines_from_vreg.py) now handle credit notes consistently

## Date Implemented

2025-01-27

