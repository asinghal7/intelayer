# Database Schema - Final State

## Overview

This document describes the complete database schema for the Intelayer ERP analytics system. The schema follows a dimensional modeling approach with fact and dimension tables, optimized for analytics and reporting.

## Schema Evolution

The database has evolved through the following migrations:

1. **0001_cdm.sql** - Initial Common Dimensional Model
2. **0002_add_vchtype.sql** - Added voucher type to fact_invoice
3. **0003_dim_pincode.sql** - Added pincode dimension table
4. **0004_stock_masters.sql** - Extended item table and added stock groups
5. **0005_brand_flag.sql** - Added brand flag to items
6. **0006_fact_invoice_line.sql** - Added line-level invoice details
7. **0007_ledger_masters.sql** - Added ledger group hierarchy and customer ledger group assignment

---

## Dimension Tables

### dim_customer

Customer master data with location information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `customer_id` | text | PRIMARY KEY | Unique customer identifier |
| `name` | text | NOT NULL | Customer name |
| `gstin` | text | | GST identification number |
| `city` | text | | Customer city |
| `pincode` | text | | Postal code |
| `ledger_group_name` | text | | Ledger group this customer belongs to |
| `created_at` | timestamptz | DEFAULT now() | Record creation timestamp |

**Indexes:**
- Primary key on `customer_id`
- Index on `ledger_group_name`

**Usage:**
- Links to `fact_invoice.customer_id`
- Links to `fact_receipt.customer_id`
- References `dim_ledger_group.name` via `ledger_group_name`

**Notes:**
- `ledger_group_name` added in migration 0007
- Enables customer segmentation by ledger groups (e.g., "Sundry Debtors", "North Zone Debtors")

---

### dim_item

Stock item master data with hierarchy and categorization.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `item_id` | text | PRIMARY KEY | Unique item identifier |
| `sku` | text | | SKU code |
| `name` | text | NOT NULL | Item name |
| `brand` | text | | Brand name |
| `hsn` | text | | HSN code for tax |
| `uom` | text | | Unit of measure |
| `guid` | text | UNIQUE | Tally GUID |
| `parent_name` | text | | Stock group parent |
| `created_at` | timestamptz | DEFAULT now() | Record creation timestamp |
| `updated_at` | timestamptz | DEFAULT now() | Last update timestamp |

**Indexes:**
- Primary key on `item_id`
- Unique index on `guid`
- Index on `parent_name`
- Index on `brand`

**Usage:**
- Links to `fact_invoice_line.sku_id`

**Notes:**
- `guid` added in migration 0004 for Tally integration
- `parent_name` links to `dim_stock_group` hierarchy
- `updated_at` tracks last sync from Tally masters

---

### dim_stock_group

Stock group hierarchy for item categorization.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `stock_group_id` | bigserial | PRIMARY KEY | Auto-increment ID |
| `guid` | text | UNIQUE | Tally GUID |
| `name` | text | UNIQUE NOT NULL | Stock group name |
| `parent_name` | text | | Parent group name |
| `alter_id` | bigint | | Tally alter ID |
| `updated_at` | timestamptz | DEFAULT now() | Last update timestamp |

**Indexes:**
- Primary key on `stock_group_id`
- Unique index on `guid`
- Unique index on `name`
- Index on `parent_name`

**Usage:**
- Hierarchical categorization of items
- Used for grouping and reporting

**Notes:**
- Created in migration 0004
- Supports multi-level hierarchy via `parent_name`

---

### dim_ledger_group

Ledger group hierarchy for customer/ledger categorization.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `ledger_group_id` | bigserial | PRIMARY KEY | Auto-increment ID |
| `guid` | text | UNIQUE | Tally GUID |
| `name` | text | UNIQUE NOT NULL | Ledger group name |
| `parent_name` | text | | Parent group name |
| `alter_id` | bigint | | Tally alter ID |
| `updated_at` | timestamptz | DEFAULT now() | Last update timestamp |

**Indexes:**
- Primary key on `ledger_group_id`
- Unique index on `guid`
- Unique index on `name`
- Index on `parent_name`

**Usage:**
- Hierarchical categorization of customers/ledgers
- Enables customer segmentation (e.g., "Sundry Debtors", "North Zone Debtors")
- Referenced by `dim_customer.ledger_group_name`

**Notes:**
- Created in migration 0007
- Supports multi-level hierarchy via `parent_name`
- Example hierarchy: Sundry Debtors → North Zone Debtors → Delhi Customers

---

### dim_uom

Unit of measure catalog.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `uom_name` | text | PRIMARY KEY | UOM name (e.g., "Nos", "Kg") |
| `original_name` | text | | Original name from Tally |
| `gst_rep_uom` | text | | GST reporting UOM |
| `is_simple` | boolean | | Simple unit flag |
| `alter_id` | bigint | | Tally alter ID |
| `updated_at` | timestamptz | DEFAULT now() | Last update timestamp |

**Indexes:**
- Primary key on `uom_name`

**Usage:**
- Standardized unit definitions
- Links to items and invoice lines

**Notes:**
- Created in migration 0004
- Used for quantity standardization

---

### dim_salesperson

Salesperson master data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `sp_id` | text | PRIMARY KEY | Salesperson ID |
| `name` | text | NOT NULL | Salesperson name |

**Indexes:**
- Primary key on `sp_id`

**Usage:**
- Links to `fact_invoice.sp_id`

---

### dim_pincode

Indian postal code reference data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `pincode` | text | PRIMARY KEY | 6-digit postal code |
| `office_name` | text | | Post office name |
| `district` | text | | District name |
| `state` | text | | State name |
| `latitude` | numeric(10,7) | | GPS latitude |
| `longitude` | numeric(10,7) | | GPS longitude |

**Indexes:**
- Primary key on `pincode`

**Usage:**
- Reference data for customer locations
- Enables geographic analysis

**Notes:**
- Created in migration 0003
- Populated from Indian postal service data

---

## Fact Tables

### fact_invoice

Invoice header-level transaction data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `invoice_id` | text | PRIMARY KEY | Unique invoice identifier (GUID or composite) |
| `voucher_key` | text | UNIQUE | Voucher key for deduplication |
| `vchtype` | text | | Voucher type (Sales, Invoice, etc.) |
| `date` | date | NOT NULL | Invoice date |
| `customer_id` | text | FK → dim_customer | Customer reference |
| `sp_id` | text | FK → dim_salesperson | Salesperson reference |
| `subtotal` | numeric | NOT NULL | Pre-tax amount |
| `tax` | numeric | NOT NULL | Tax amount |
| `total` | numeric | NOT NULL | Total amount (subtotal + tax) |
| `roundoff` | numeric | DEFAULT 0 | Rounding adjustment |

**Indexes:**
- Primary key on `invoice_id`
- Unique index on `voucher_key`
- Index on `date`
- Index on `customer_id`
- Index on `vchtype`

**Usage:**
- Header-level invoice data
- Links to `fact_invoice_line` for line details

**Notes:**
- `vchtype` added in migration 0002
- Uses `ON CONFLICT` for upsert logic
- Supports all voucher types from Tally

---

### fact_invoice_line

Line-level invoice details with item quantities and pricing.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `invoice_line_id` | bigserial | PRIMARY KEY | Auto-increment line ID |
| `invoice_id` | text | FK → fact_invoice | Invoice reference |
| `sku_id` | text | FK → dim_item | Item reference (nullable) |
| `sku_name` | text | | Item name (denormalized) |
| `qty` | numeric(14,3) | | Quantity |
| `uom` | text | | Unit of measure |
| `rate` | numeric(14,2) | | Rate per unit |
| `discount` | numeric(14,2) | | Line discount |
| `line_basic` | numeric(14,2) | | Pre-tax line amount |
| `line_tax` | numeric(14,2) | | Allocated tax |
| `line_total` | numeric(14,2) | | Total (basic + tax) |
| `created_at` | timestamptz | DEFAULT now() | Record creation timestamp |

**Indexes:**
- Primary key on `invoice_line_id`
- Index on `invoice_id`
- Index on `sku_id`

**Usage:**
- Detailed line-item data
- Enables "who bought which SKU" queries
- Supports item-level analytics

**Notes:**
- Created in migration 0006
- Tax allocated proportionally: `line_tax = (line_basic / sum_line_basic) * voucher_tax`
- Cascade delete when invoice is deleted

---

### fact_receipt

Receipt/payment transaction data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | bigserial | PRIMARY KEY | Auto-increment ID |
| `receipt_key` | text | UNIQUE | Receipt key for deduplication |
| `date` | date | NOT NULL | Receipt date |
| `customer_id` | text | FK → dim_customer | Customer reference |
| `amount` | numeric | NOT NULL | Receipt amount |

**Indexes:**
- Primary key on `id`
- Unique index on `receipt_key`
- Index on `date`

**Usage:**
- Payment/receipt transactions
- Cash flow tracking

---

## Staging Tables

### stg_vreg_header

Staging table for voucher register headers.

| Column | Type | Description |
|--------|------|-------------|
| `guid` | text | Voucher GUID |
| `vch_no` | text | Voucher number |
| `vch_date` | date | Voucher date |
| `party` | text | Party/customer name |
| `basic_amount` | numeric(14,2) | Pre-tax amount |
| `tax_amount` | numeric(14,2) | Tax amount |
| `total_amount` | numeric(14,2) | Total amount |

**Usage:**
- Temporary staging during ETL
- Truncated before each batch

---

### stg_vreg_line

Staging table for voucher register line items.

| Column | Type | Description |
|--------|------|-------------|
| `voucher_guid` | text | Voucher GUID |
| `stock_item_name` | text | Item name |
| `billed_qty` | text | Billed quantity (e.g., "2 Nos") |
| `rate` | text | Rate (e.g., "35000 / Nos") |
| `amount` | numeric(14,2) | Line amount |
| `discount` | numeric(14,2) | Line discount |

**Usage:**
- Temporary staging during ETL
- Truncated before each batch
- Raw data before parsing

---

## Operational Tables

### etl_checkpoints

ETL checkpoint tracking for incremental processing.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `stream_name` | text | PRIMARY KEY | ETL stream name |
| `last_date` | date | | Last processed date |
| `last_key` | text | | Last processed key |
| `updated_at` | timestamptz | DEFAULT now() | Last update timestamp |

**Indexes:**
- Primary key on `stream_name`

**Usage:**
- Tracks last processed date per stream
- Enables incremental ETL runs
- Prevents duplicate processing

**Example Streams:**
- `invoices` - Invoice processing
- `receipts` - Receipt processing
- `sales-lines` - Sales lines processing

---

### etl_logs

ETL execution logs for monitoring and debugging.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | bigserial | PRIMARY KEY | Auto-increment log ID |
| `stream_name` | text | | ETL stream name |
| `run_at` | timestamptz | DEFAULT now() | Execution timestamp |
| `rows` | int | | Rows processed |
| `status` | text | | Status (ok, error) |
| `error` | text | | Error message (if any) |

**Indexes:**
- Primary key on `id`

**Usage:**
- Audit trail of ETL executions
- Error tracking and debugging
- Performance monitoring

---

## Relationships

### Entity Relationship Diagram

```
dim_customer ──┬── fact_invoice
               ├── fact_receipt
               └── dim_ledger_group (via ledger_group_name)

dim_salesperson ── fact_invoice

dim_item ────────── fact_invoice_line
                         │
                         └── fact_invoice (via invoice_id)

dim_stock_group ─── dim_item (via parent_name)
```

### Key Relationships

1. **fact_invoice → dim_customer**
   - Many invoices to one customer
   - Foreign key: `customer_id`

2. **fact_invoice → dim_salesperson**
   - Many invoices to one salesperson
   - Foreign key: `sp_id`

3. **fact_invoice_line → fact_invoice**
   - Many lines to one invoice
   - Foreign key: `invoice_id`
   - Cascade delete

4. **fact_invoice_line → dim_item**
   - Many lines to one item
   - Foreign key: `sku_id`
   - Nullable (for unmapped items)

5. **dim_item → dim_stock_group**
   - Many items to one stock group
   - Relationship via `parent_name`

6. **dim_customer → dim_ledger_group**
   - Many customers to one ledger group
   - Relationship via `ledger_group_name`
   - Enables customer segmentation

---

## Data Types

### Numeric Precision

- **Amounts**: `numeric(14,2)` - Up to 999,999,999,999.99
- **Quantities**: `numeric(14,3)` - Up to 999,999,999,999.999
- **Coordinates**: `numeric(10,7)` - GPS precision

### Text Fields

- **IDs**: `text` - Flexible length for GUIDs and composite keys
- **Names**: `text` - Variable length strings
- **Codes**: `text` - SKU, HSN, GSTIN codes

### Temporal Fields

- **Dates**: `date` - ISO date format
- **Timestamps**: `timestamptz` - Timezone-aware timestamps

---

## Indexes Summary

### Primary Keys
- All dimension and fact tables have primary keys
- Most use `text` type for business keys
- Some use `bigserial` for surrogate keys

### Foreign Keys
- All foreign key relationships are indexed
- Cascade delete on `fact_invoice_line`

### Performance Indexes
- Date indexes on all fact tables
- Customer indexes for customer queries
- Brand and group indexes for item filtering

---

## Data Quality

### Constraints

1. **NOT NULL**: Required fields enforced
2. **UNIQUE**: Prevents duplicate records
3. **FOREIGN KEY**: Referential integrity
4. **CHECK**: Numeric ranges (implicit via precision)

### Nullability

**Nullable Fields:**
- `sku_id` - Items may not be in master
- `sp_id` - Invoices may not have salesperson
- `gstin`, `pincode`, `city` - Optional customer data
- `discount` - Not all lines have discounts

**NOT NULL Fields:**
- All IDs and keys
- All fact table amounts
- All dates
- Item names and customer names

---

## Migration History

### 0001_cdm.sql (Initial Schema)
- Created core dimension tables
- Created fact_invoice and fact_receipt
- Created operational tables
- Established base indexes

### 0002_add_vchtype.sql
- Added `vchtype` to fact_invoice
- Added index on vchtype

### 0003_dim_pincode.sql
- Created dim_pincode table
- Populated with Indian postal data

### 0004_stock_masters.sql
- Created dim_stock_group table
- Created dim_uom table
- Extended dim_item with guid, parent_name, updated_at
- Added indexes on parent_name and brand

### 0005_brand_flag.sql
- Added brand flag to dim_item (if needed)

### 0006_fact_invoice_line.sql
- Created fact_invoice_line table
- Created staging tables (stg_vreg_header, stg_vreg_line)
- Added indexes for line queries

### 0007_ledger_masters.sql
- Created dim_ledger_group table for ledger group hierarchy
- Added ledger_group_name column to dim_customer
- Added indexes for performance
- Enables customer segmentation by ledger groups

---

## Best Practices

### Querying

1. **Always join on indexed columns**
   - Use invoice_id, customer_id, date
   - Avoid full table scans

2. **Use date ranges**
   - Filter by date for performance
   - Leverage date indexes

3. **Aggregate at fact level**
   - Pre-aggregate for reporting
   - Use materialized views for heavy queries

### Maintenance

1. **Regular VACUUM**
   - Clean up deleted rows
   - Update statistics

2. **Monitor index usage**
   - Drop unused indexes
   - Add missing indexes

3. **Archive old data**
   - Move old invoices to archive tables
   - Keep recent data hot

### Data Loading

1. **Use staging tables**
   - Load to staging first
   - Validate before fact tables

2. **Batch processing**
   - Use checkpoints for incremental loads
   - Process in 15-day chunks

3. **Handle conflicts**
   - Use ON CONFLICT for upserts
   - Delete and re-insert for lines

---

## Common Queries

### Sales by Customer
```sql
select 
  dc.name as customer,
  count(distinct fi.invoice_id) as invoice_count,
  sum(fi.total) as total_sales
from fact_invoice fi
join dim_customer dc on dc.customer_id = fi.customer_id
where fi.date between '2025-09-01' and '2025-09-30'
group by dc.name
order by total_sales desc;
```

### Top Selling Items
```sql
select 
  fil.sku_name,
  sum(fil.qty) as total_qty,
  sum(fil.line_total) as total_revenue
from fact_invoice_line fil
join fact_invoice fi on fi.invoice_id = fil.invoice_id
where fi.date between '2025-09-01' and '2025-09-30'
group by fil.sku_name
order by total_revenue desc
limit 20;
```

### Line-Level Details
```sql
select 
  fi.date,
  fi.voucher_key,
  dc.name as customer,
  fil.sku_name,
  fil.qty,
  fil.uom,
  fil.rate,
  fil.line_total
from fact_invoice fi
join fact_invoice_line fil on fil.invoice_id = fi.invoice_id
left join dim_customer dc on dc.customer_id = fi.customer_id
where fi.date between '2025-09-01' and '2025-09-30'
order by fi.date desc, fi.voucher_key;
```

### Sales by Ledger Group
```sql
select 
  dc.ledger_group_name,
  count(distinct dc.customer_id) as customer_count,
  count(distinct fi.invoice_id) as invoice_count,
  sum(fi.total) as total_sales
from fact_invoice fi
join dim_customer dc on dc.customer_id = fi.customer_id
where fi.date between '2025-09-01' and '2025-09-30'
  and dc.ledger_group_name is not null
group by dc.ledger_group_name
order by total_sales desc;
```

---

## Related Documentation

- `SALES_LINES_USAGE.md` - Sales lines ETL usage guide
- `STOCK_MASTER_USAGE.md` - Stock masters ETL
- `LEDGER_MASTER_USAGE.md` - Ledger masters ETL
- `BACKFILL_GUIDE.md` - Data backfill procedures
- `SETUP_INSTRUCTIONS.md` - Initial setup guide

