# Pincode Dimension Table Setup

## Summary

Successfully created and populated the `dim_pincode` table with Indian pincode data from `pincodemapvf.csv`.

---

## Table Schema

```sql
CREATE TABLE dim_pincode (
  pincode  TEXT PRIMARY KEY,
  city     TEXT,
  state    TEXT,
  lat      NUMERIC,   -- centroid latitude
  lon      NUMERIC    -- centroid longitude
);

CREATE INDEX idx_dim_pincode_state ON dim_pincode(state);
```

---

## Data Loaded

### Statistics
- **Total Pincodes**: 1,668 unique pincodes
- **Source File**: `pincodemapvf.csv` (17,968 rows)
- **Duplicates Skipped**: 16,300 (kept first occurrence of each pincode)
- **Missing Coordinates**: 56 pincodes have NULL lat/lon

### Geographic Distribution
All pincodes in the dataset are from:
- **Uttar Pradesh**: 1,668 pincodes

### Sample Data
```
229211 - Rae Bareli, Uttar Pradesh (lat: 27.11, lon: 83.5)
229001 - Rae Bareli, Uttar Pradesh (lat: 26.23, lon: 81.21)
229301 - Rae Bareli, Uttar Pradesh (lat: 20.49, lon: 85.94)
```

---

## Files Created

### 1. Migration File
**Location**: `warehouse/migrations/0003_dim_pincode.sql`

Contains the DDL for creating the table and index.

### 2. Data Loader Script
**Location**: `load_pincode_data.py`

Python script to load data from CSV into the database.

**Usage**:
```bash
python load_pincode_data.py
```

**Features**:
- Handles duplicate pincodes (keeps first occurrence)
- Handles missing/invalid coordinates ('NA' values)
- Uses UPSERT for idempotent loading
- Provides detailed logging

---

## Database Indexes

### Primary Key
- `dim_pincode_pkey` - UNIQUE index on `pincode` column

### Secondary Index
- `idx_dim_pincode_state` - B-tree index on `state` column for faster state-based lookups

---

## Data Quality

### Handling Missing Data
- **Coordinates**: 56 pincodes have NULL lat/lon (valid entries with 'NA' in source)
- **City/State**: All records have valid city and state values
- **Duplicates**: Automatically handled by keeping first occurrence

### Data Transformations
- **City**: District name from CSV, title-cased
- **State**: State name from CSV, title-cased
- **Lat/Lon**: Numeric conversion with NA handling

---

## Usage Examples

### Find pincode details
```sql
SELECT * FROM dim_pincode WHERE pincode = '229211';
```

### Get all pincodes in a state
```sql
SELECT pincode, city 
FROM dim_pincode 
WHERE state = 'Uttar Pradesh'
ORDER BY pincode;
```

### Find nearby pincodes (using coordinates)
```sql
SELECT pincode, city, 
       SQRT(POWER(lat - 27.11, 2) + POWER(lon - 83.5, 2)) AS distance
FROM dim_pincode
WHERE lat IS NOT NULL AND lon IS NOT NULL
ORDER BY distance
LIMIT 10;
```

### Join with customer data
```sql
SELECT c.customer_id, c.name, p.city, p.state
FROM dim_customer c
LEFT JOIN dim_pincode p ON c.pincode = p.pincode
WHERE c.pincode IS NOT NULL;
```

---

## Reloading Data

To reload data (e.g., after updating the CSV):

```bash
# Simply run the loader again (it will upsert)
python load_pincode_data.py
```

The script uses `ON CONFLICT ... DO UPDATE` so it's safe to run multiple times.

---

## Future Enhancements

Possible improvements:
1. **Add more pincodes**: Current dataset only has Uttar Pradesh
2. **Geocoding**: Fill missing coordinates using geocoding API
3. **Validation**: Add constraints for pincode format (6 digits)
4. **Additional fields**: Add region, division, office name if needed
5. **PostGIS**: Use PostGIS for advanced geographic queries

---

## Notes

- The CSV had 17,968 rows but many duplicate pincodes
- Only 1,668 unique pincodes were loaded
- All pincodes are from Uttar Pradesh (Rae Bareli district area)
- If you need nationwide pincode data, you'll need a more complete dataset

---

## Verification

Run a quick verification:

```sql
-- Check total count
SELECT COUNT(*) FROM dim_pincode;

-- Check states
SELECT state, COUNT(*) 
FROM dim_pincode 
GROUP BY state;

-- Check for missing data
SELECT 
  COUNT(*) FILTER (WHERE lat IS NULL) as missing_lat,
  COUNT(*) FILTER (WHERE lon IS NULL) as missing_lon,
  COUNT(*) FILTER (WHERE city IS NULL) as missing_city,
  COUNT(*) FILTER (WHERE state IS NULL) as missing_state
FROM dim_pincode;
```

---

## Conclusion

✅ Table created successfully
✅ Data loaded: 1,668 pincodes
✅ Indexes created for optimal performance
✅ Ready for use in queries and joins

The `dim_pincode` table is now ready to enrich customer data with geographic information!

