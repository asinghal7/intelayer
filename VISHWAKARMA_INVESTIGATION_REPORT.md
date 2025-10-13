# Vishwakarma Bandhu Investigation Report

## Problem Statement

**Invoice:** Vishwakarma Bandhu  
**Expected:** Subtotal = 78,559.29 (pre-tax), Total = 92,700.00 (post-tax), Tax = 14,140.71  
**Actual:** Subtotal = 78,559.29, Total = 78,559.29, Tax = 0.00  
**Issue:** Tax column showing 0 despite invoice having 18% GST

## Root Cause Identified ✓

### The Vishwakarma invoice uses a DIFFERENT XML structure:

**Standard invoices (working correctly):**
```xml
<VOUCHER>
  <ALLINVENTORYENTRIES.LIST>
    <!-- Pre-tax amounts -->
  </ALLINVENTORYENTRIES.LIST>
  <BILLALLOCATIONS.LIST>
    <AMOUNT>-127076.00</AMOUNT>  ← Post-tax total HERE
  </BILLALLOCATIONS.LIST>
</VOUCHER>
```

**Vishwakarma invoice (not working):**
```xml
<VOUCHER>
  <ALLINVENTORYENTRIES.LIST>
    <!-- Pre-tax amounts: 78,559.29 -->
  </ALLINVENTORYENTRIES.LIST>
  <BILLALLOCATIONS.LIST>
    <!-- EMPTY! No AMOUNT field -->
  </BILLALLOCATIONS.LIST>
  <LEDGERENTRIES.LIST>           ← Different tag!
    <LEDGERNAME>Vishwakarma Bandhu</LEDGERNAME>
    <AMOUNT>-92700.00</AMOUNT>    ← Post-tax total HERE instead!
  </LEDGERENTRIES.LIST>
</VOUCHER>
```

### Key Differences

| Element | Other Invoices | Vishwakarma |
|---------|---------------|-------------|
| Inventory entries | `ALLINVENTORYENTRIES.LIST` ✓ | `ALLINVENTORYENTRIES.LIST` ✓ |
| Bill allocations | `BILLALLOCATIONS.LIST/AMOUNT` ✓ | `BILLALLOCATIONS.LIST` (empty) ✗ |
| Ledger entries | `ALLLEDGERENTRIES.LIST` (or none) | `LEDGERENTRIES.LIST` ← Single R! |
| Party amount location | BILLALLOCATIONS | LEDGERENTRIES |

## Detailed Analysis

### Amounts Found

From `LEDGERENTRIES.LIST`:
```
Vishwakarma Bandhu    : -92,700.00  (Customer debit - total with tax)
CGST                  :   7,070.34  (Central GST)
SGST                  :   7,070.34  (State GST)
Rounding Off          :       0.03  (Rounding adjustment)
```

### Tax Calculation Verification

```
Pre-tax amount  : 78,559.29 (from inventory)
CGST (9%)       :  7,070.34
SGST (9%)       :  7,070.34
Tax total (18%) : 14,140.68
Rounding        :      0.03
─────────────────────────────
Post-tax total  : 92,700.00 ✓ Matches expected!
```

### Why Current Parser Misses It

**Current parser logic:**

1. `_bill_allocation_amount()` - Looks for `.//BILLALLOCATIONS.LIST/AMOUNT`
   - ✗ Vishwakarma has BILLALLOCATIONS.LIST but no AMOUNT child

2. `_party_line_amount_signed()` - Looks for `.//ALLLEDGERENTRIES.LIST` (double L)
   - ✗ Vishwakarma has LEDGERENTRIES.LIST (single R)

3. `_fallback_amount_signed()` - Looks for `.//ALLLEDGERENTRIES.LIST` (double L)
   - ✗ Vishwakarma has LEDGERENTRIES.LIST (single R)

4. Falls back to inventory total → Gets 78,559.29 (pre-tax) for both subtotal and total

## Solution Proposed

Update parser functions to check **both** variants:
- `ALLLEDGERENTRIES.LIST` (double L) ← Currently checked
- `LEDGERENTRIES.LIST` (single R) ← Need to add

### Functions to Update

1. **`_party_line_amount_signed()`** - Add check for `LEDGERENTRIES.LIST`
2. **`_fallback_amount_signed()`** - Add check for `LEDGERENTRIES.LIST`

### Implementation Strategy

```python
def _party_line_amount_signed(voucher: etree._Element, party_name: str) -> float | None:
    party = (party_name or "").strip().lower()
    
    # Check ALLLEDGERENTRIES.LIST (double L) - standard format
    for le in voucher.findall(".//ALLLEDGERENTRIES.LIST"):
        lname = (le.findtext("LEDGERNAME") or "").strip().lower()
        if lname == party:
            return _to_float(le.findtext("AMOUNT"))
    
    # Check LEDGERENTRIES.LIST (single R) - alternate format
    for le in voucher.findall(".//LEDGERENTRIES.LIST"):
        lname = (le.findtext("LEDGERNAME") or "").strip().lower()
        if lname == party:
            return _to_float(le.findtext("AMOUNT"))
    
    return None
```

## Why This Happens

Tally XML export format varies based on:
- Tally version
- Voucher configuration
- Company settings
- Invoice type (some use ALLLEDGERENTRIES, some use LEDGERENTRIES)

This is a **known variation** in Tally's XML export format.

## Testing Plan

### Before Fix
```
Vishwakarma Bandhu: Subtotal=78,559.29, Tax=0.00, Total=78,559.29 ✗
```

### After Fix
```
Vishwakarma Bandhu: Subtotal=78,559.29, Tax=14,140.71, Total=92,700.00 ✓
```

### Regression Testing

Ensure other invoices still work:
```
New P.K. #1        : Subtotal=107,691.50, Tax=19,384.50, Total=127,076.00 ✓
New P.K. #2        : Subtotal= 89,152.52, Tax=16,047.48, Total=105,200.00 ✓
Khanna Radios #1   : Subtotal= 96,850.84, Tax=17,433.16, Total=114,284.00 ✓
Khanna Radios #2   : Subtotal=126,199.17, Tax=22,715.83, Total=148,915.00 ✓
```

## Risk Assessment

### Low Risk
- Adding fallback check for alternate tag name
- Only affects vouchers that currently fail (Vishwakarma type)
- Existing working invoices continue to use BILLALLOCATIONS or ALLLEDGERENTRIES

### Testing Required
- Run all existing tests
- Verify Vishwakarma now shows correct amounts
- Verify other invoices unchanged

## Additional Observations

### CGST/SGST Breakdown

The Vishwakarma invoice shows GST split:
- **CGST (Central)**: 7,070.34 (9%)
- **SGST (State)**: 7,070.34 (9%)
- **Total GST**: 14,140.68 (18%)

This is standard for intra-state transactions in India (CGST + SGST = 18%)

### Rounding

The invoice has a "Rounding Off" ledger with 0.03:
```
Tax calculation: 78,559.29 × 18% = 14,140.67
Rounded to:      14,140.71
Rounding adj:    0.03 (or 14,140.68 + 0.03 = 14,140.71)
```

## Conclusion

The Vishwakarma invoice is **perfectly valid** and follows an **alternate Tally XML format** using `LEDGERENTRIES.LIST` instead of `ALLLEDGERENTRIES.LIST`. The parser needs to be updated to handle both formats.

**Impact:** Once fixed, this will likely resolve similar issues for any other invoices using the same XML structure.

## Files to Modify

1. **`adapters/tally_http/parser.py`**
   - `_party_line_amount_signed()` - Add LEDGERENTRIES.LIST check
   - `_fallback_amount_signed()` - Add LEDGERENTRIES.LIST check

## Next Steps

1. Review and approve proposed solution
2. Implement parser updates
3. Run full test suite
4. Verify Vishwakarma invoice
5. Verify all other invoices unchanged
6. Document the dual-format support

---

**Investigation Status:** ✅ COMPLETE  
**Root Cause:** Identified  
**Solution:** Proposed  
**Ready for Implementation:** Yes (pending approval)

