# Customer Details Extraction - GSTIN & Pincode

## Summary

Enhanced the Tally extraction pipeline to capture and store customer master data (GSTIN, Pincode, City) from Tally during `run` and `backfill` operations.

## Important Note on Tally Reports

**Voucher Register vs DayBook**: This implementation uses **Voucher Register** (not DayBook) because:
- Voucher Register correctly respects date filters (`SVFROMDATE` and `SVTODATE`)
- DayBook ignores date filters and returns current day's data regardless of date parameters
- This is critical for backfill operations to fetch historical data correctly

## Changes Made

### 1. Parser Enhancement (`adapters/tally_http/parser.py`)
- **Modified**: `parse_daybook()` function
- **Added**: Extraction logic for three new fields from Tally XML:
  - `party_gstin` - Customer's GSTIN (GST Identification Number)
  - `party_pincode` - Customer's postal/PIN code
  - `party_city` - Customer's city/state
- **XML Paths Checked**: The parser attempts multiple XML paths to find these fields:
  - Direct fields: `PARTYGSTIN`, `PARTYPINCODE`, `PARTYCITY`
  - Nested fields: `.//BASICBUYERPARTYGSTIN`, `.//BASICBUYERPINCODE`, `.//BASICBUYERSTATE`
- **Behavior**: Returns `None` if fields are not present in XML (backward compatible)

### 2. Adapter Update (`adapters/tally_http/adapter.py`)
- **Modified**: `TallyHTTPAdapter.fetch_invoices()` method
- **Added**: Extraction and attachment of customer details to Invoice objects
- **Implementation**: Customer data is attached as private attributes (`_customer_gstin`, `_customer_pincode`, `_customer_city`) to Invoice objects for downstream processing

### 3. Database Upsert Logic (`agent/run.py`)
- **Modified**: `upsert_customer()` function signature and implementation
- **New Parameters**: `gstin`, `pincode`, `city` (all optional)
- **SQL Strategy**: Uses `COALESCE` to preserve existing non-null values while allowing updates when new data is available
- **Modified**: `upsert_invoice()` to extract customer details from Invoice object and pass to `upsert_customer()`

### 4. Tally XML Request Template (`adapters/tally_http/requests/daybook.xml.j2`)
- **Status**: No changes to report type
- **Uses**: `Voucher Register` (critical for date filter support)
- **Note**: DayBook was NOT used as it ignores date filters

### 5. Database Schema (`warehouse/ddl/0001_cdm.sql`)
- **Status**: Already includes required columns (no changes needed)
- **Columns**: `gstin`, `pincode`, `city` already exist in `dim_customer` table

### 6. Test Coverage (`tests/test_parser_daybook.py`)
- **Added**: Test fixture with customer details (`daybook_with_customer_details.xml`)
- **Added**: `test_parse_daybook_with_customer_details()` - Verifies extraction of all three fields
- **Added**: `test_parse_daybook_without_customer_details()` - Verifies graceful handling of missing data

## How It Works

### Data Flow
1. **Tally XML Export** → Contains voucher data with embedded party/customer information
2. **Parser** → Extracts customer details (GSTIN, pincode, city) along with voucher data
3. **Adapter** → Attaches customer details to Invoice objects as private attributes
4. **Agent** → Extracts customer details and upserts into `dim_customer` table

### SQL Upsert Behavior
```sql
INSERT INTO dim_customer (customer_id, name, gstin, pincode, city)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (customer_id) DO UPDATE SET
  gstin = COALESCE(excluded.gstin, dim_customer.gstin),
  pincode = COALESCE(excluded.pincode, dim_customer.pincode),
  city = COALESCE(excluded.city, dim_customer.city)
```

This ensures:
- New customers get all available data
- Existing customers get updated only if new non-null data is available
- Existing non-null values are never overwritten with nulls

## Usage

### Normal Run
```bash
python -m agent.run
```
Customer details are automatically extracted and stored during daily runs.

### Backfill
```bash
python -m agent.backfill 2024-04-01 2024-10-13
```
Customer details are extracted and stored for historical data as well.

## Tally Configuration

### What's Included Automatically
For Tally to include customer details in voucher exports, the following should be configured:
1. **Party Master** should have GSTIN, Address configured
2. **Vouchers** should reference the party ledger

### Expected XML Structure
When Tally is properly configured, the XML export will include:
```xml
<VOUCHER VCHTYPE="Sales" VCHNUMBER="S-101">
  <PARTYLEDGERNAME>Customer Name</PARTYLEDGERNAME>
  <PARTYGSTIN>27AABCU9603R1ZM</PARTYGSTIN>
  <PARTYPINCODE>400001</PARTYPINCODE>
  <PARTYCITY>Maharashtra</PARTYCITY>
  ...
</VOUCHER>
```

## Notes & Limitations

1. **Tally Version Dependent**: Field names may vary between Tally versions. The parser checks multiple possible field names.
2. **Optional Data**: If Tally doesn't export these fields (e.g., party master incomplete), they will be stored as NULL.
3. **Backward Compatible**: Existing functionality continues to work even if customer details are not available.
4. **Incremental Updates**: If customer details become available later (e.g., after updating Tally masters), they will be populated on subsequent runs.

## Testing

Run tests to verify functionality:
```bash
# Test parser only
pytest tests/test_parser_daybook.py -v

# Run all tests
pytest tests/ -v
```

All tests should pass (14 total).

## Future Enhancements

Possible future improvements:
- Add customer master export (separate from vouchers) for complete customer data
- Add validation for GSTIN format (15 characters)
- Add validation for pincode format (6 digits)
- Extract additional customer fields (email, phone, address lines)
- Create separate customer sync job for periodic master data refresh

