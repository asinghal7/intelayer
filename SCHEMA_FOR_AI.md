# Database Schema for AI

## System Purpose

This is a data warehouse for an ERP analytics system that extracts data from Tally ERP software and stores it in PostgreSQL. The system tracks sales transactions, customer information, inventory items, and payments.

## Table Overview

The database has 16 tables organized into 4 categories:

1. **Dimension Tables (6)**: Master data that describes entities
2. **Fact Tables (3)**: Transaction data with measurements
3. **Staging Tables (2)**: Temporary tables for data loading
4. **Operational Tables (2)**: ETL tracking and logging

---

## DIMENSION TABLES

### Table: dim_customer

**Purpose**: Stores customer master data including contact and location information.

**Columns**:
- customer_id (text, primary key) - Unique identifier for each customer
- name (text, required) - Customer's business name
- gstin (text, optional) - Goods and Services Tax Identification Number
- city (text, optional) - Customer's city
- pincode (text, optional) - Postal code
- created_at (timestamp) - When this record was created

**Key Relationships**:
- Referenced by: fact_invoice.customer_id, fact_receipt.customer_id
- References: dim_pincode.pincode (indirectly via pincode field)

**Example Data**:
```
customer_id: "CUST001"
name: "ABC Corporation"
gstin: "27AAECA1234M1Z5"
city: "Mumbai"
pincode: "400001"
```

---

### Table: dim_item

**Purpose**: Stores inventory item master data including products, materials, and SKUs.

**Columns**:
- item_id (text, primary key) - Unique identifier for each item
- sku (text, optional) - Stock Keeping Unit code
- name (text, required) - Item name/description
- brand (text, optional) - Brand name
- hsn (text, optional) - Harmonized System Nomenclature code for tax classification
- uom (text, optional) - Unit of measure (Nos, Kg, Ltr, etc.)
- guid (text, unique, optional) - Tally ERP system GUID
- parent_name (text, optional) - Parent stock group name for hierarchy
- created_at (timestamp) - When this record was created
- updated_at (timestamp) - When this record was last updated

**Key Relationships**:
- Referenced by: fact_invoice_line.sku_id
- References: dim_stock_group.name (via parent_name field)

**Example Data**:
```
item_id: "ITEM001"
sku: "SKU-12345"
name: "Premium Widget 500g"
brand: "BrandX"
hsn: "12345678"
uom: "Nos"
guid: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
parent_name: "Electronics"
```

---

### Table: dim_stock_group

**Purpose**: Defines hierarchical categorization of inventory items (e.g., Electronics > Mobile Phones > Accessories).

**Columns**:
- stock_group_id (bigserial, primary key) - Auto-incrementing ID
- guid (text, unique, optional) - Tally ERP system GUID
- name (text, unique, required) - Stock group name
- parent_name (text, optional) - Parent group name for hierarchy
- alter_id (bigint, optional) - Tally alteration ID
- updated_at (timestamp) - Last update timestamp

**Key Relationships**:
- Referenced by: dim_item.parent_name

**Hierarchy Example**:
```
Electronics (parent_name: NULL)
  ├── Mobile Phones (parent_name: "Electronics")
  │   ├── Accessories (parent_name: "Mobile Phones")
  │   └── Chargers (parent_name: "Mobile Phones")
  └── Computers (parent_name: "Electronics")
```

---

### Table: dim_uom

**Purpose**: Catalog of units of measure used in the system (Nos, Kg, Ltr, etc.).

**Columns**:
- uom_name (text, primary key) - Unit name
- original_name (text, optional) - Original name from Tally
- gst_rep_uom (text, optional) - GST reporting unit
- is_simple (boolean, optional) - Whether this is a simple unit
- alter_id (bigint, optional) - Tally alteration ID
- updated_at (timestamp) - Last update timestamp

**Example Data**:
```
uom_name: "Nos"
original_name: "Numbers"
gst_rep_uom: "NOS"
is_simple: true
```

---

### Table: dim_salesperson

**Purpose**: Stores information about sales representatives or salespersons.

**Columns**:
- sp_id (text, primary key) - Salesperson identifier
- name (text, required) - Salesperson name

**Key Relationships**:
- Referenced by: fact_invoice.sp_id

**Example Data**:
```
sp_id: "SP001"
name: "John Doe"
```

---

### Table: dim_pincode

**Purpose**: Indian postal code reference data with geographic coordinates.

**Columns**:
- pincode (text, primary key) - 6-digit postal code
- office_name (text, optional) - Post office name
- district (text, optional) - District name
- state (text, optional) - State name
- latitude (decimal, optional) - GPS latitude coordinate
- longitude (decimal, optional) - GPS longitude coordinate

**Example Data**:
```
pincode: "400001"
office_name: "Fort"
district: "Mumbai"
state: "Maharashtra"
latitude: 18.9387711
longitude: 72.8353355
```

---

## FACT TABLES

### Table: fact_invoice

**Purpose**: Stores invoice header-level transaction data. Each row represents one invoice or sales voucher.

**Columns**:
- invoice_id (text, primary key) - Unique invoice identifier (usually GUID or composite key)
- voucher_key (text, unique) - Voucher key for deduplication
- vchtype (text, optional) - Voucher type (Sales, Invoice, Credit Note, etc.)
- date (date, required) - Invoice date
- customer_id (text, foreign key to dim_customer) - Customer who made the purchase
- sp_id (text, foreign key to dim_salesperson, optional) - Salesperson who made the sale
- subtotal (numeric, required) - Pre-tax amount
- tax (numeric, required) - Tax amount
- total (numeric, required) - Total amount including tax
- roundoff (numeric, default 0) - Rounding adjustment

**Key Relationships**:
- References: dim_customer.customer_id, dim_salesperson.sp_id
- Referenced by: fact_invoice_line.invoice_id

**Business Rules**:
- total = subtotal + tax + roundoff
- Uses ON CONFLICT logic to update existing invoices
- Supports all voucher types from Tally

**Example Data**:
```
invoice_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
voucher_key: "INV-2025-001"
vchtype: "Sales"
date: "2025-09-15"
customer_id: "CUST001"
sp_id: "SP001"
subtotal: 100000.00
tax: 18000.00
total: 118000.00
roundoff: 0.00
```

---

### Table: fact_invoice_line

**Purpose**: Stores line-level details of each invoice. Each row represents one line item on an invoice.

**Columns**:
- invoice_line_id (bigserial, primary key) - Auto-incrementing line ID
- invoice_id (text, foreign key to fact_invoice) - Parent invoice
- sku_id (text, foreign key to dim_item, optional) - Item SKU reference
- sku_name (text, optional) - Item name (denormalized for performance)
- qty (decimal, optional) - Quantity sold
- uom (text, optional) - Unit of measure
- rate (decimal, optional) - Rate per unit
- discount (decimal, optional) - Line discount amount
- line_basic (decimal, optional) - Pre-tax line amount
- line_tax (decimal, optional) - Allocated tax for this line
- line_total (decimal, optional) - Total line amount including tax
- created_at (timestamp) - Record creation timestamp

**Key Relationships**:
- References: fact_invoice.invoice_id, dim_item.item_id (via sku_id)
- Cascade delete: When invoice is deleted, all lines are deleted

**Business Rules**:
- line_total = line_basic + line_tax
- Tax is allocated proportionally: line_tax = (line_basic / sum of all line_basic for invoice) * invoice tax
- Multiple lines per invoice (1:N relationship)

**Example Data**:
```
invoice_line_id: 1
invoice_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
sku_id: "ITEM001"
sku_name: "Premium Widget 500g"
qty: 10.000
uom: "Nos"
rate: 5000.00
discount: 0.00
line_basic: 50000.00
line_tax: 9000.00
line_total: 59000.00
```

---

### Table: fact_receipt

**Purpose**: Stores payment/receipt transaction data. Tracks when customers make payments.

**Columns**:
- id (bigserial, primary key) - Auto-incrementing ID
- receipt_key (text, unique) - Receipt key for deduplication
- date (date, required) - Receipt date
- customer_id (text, foreign key to dim_customer) - Customer who made the payment
- amount (numeric, required) - Payment amount

**Key Relationships**:
- References: dim_customer.customer_id

**Example Data**:
```
id: 1
receipt_key: "RCP-2025-001"
date: "2025-09-20"
customer_id: "CUST001"
amount: 118000.00
```

---

## STAGING TABLES

### Table: stg_vreg_header

**Purpose**: Temporary table for staging voucher header data during ETL processing. Data is truncated before each batch.

**Columns**:
- guid (text, optional) - Voucher GUID
- vch_no (text, optional) - Voucher number
- vch_date (date, optional) - Voucher date
- party (text, optional) - Party/customer name
- basic_amount (decimal, optional) - Pre-tax amount
- tax_amount (decimal, optional) - Tax amount
- total_amount (decimal, optional) - Total amount

**Usage**: Loaded from Tally XML, used to upsert fact_invoice, then truncated.

---

### Table: stg_vreg_line

**Purpose**: Temporary table for staging line item data during ETL processing. Data is truncated before each batch.

**Columns**:
- voucher_guid (text, optional) - Parent voucher GUID
- stock_item_name (text, optional) - Item name from voucher
- billed_qty (text, optional) - Billed quantity as string (e.g., "2 Nos")
- rate (text, optional) - Rate as string (e.g., "35000 / Nos")
- amount (decimal, optional) - Line amount
- discount (decimal, optional) - Line discount

**Usage**: Loaded from Tally XML, parsed to extract qty/uom/rate, then used to insert into fact_invoice_line.

---

## OPERATIONAL TABLES

### Table: etl_checkpoints

**Purpose**: Tracks the last processed date for each ETL stream to enable incremental processing.

**Columns**:
- stream_name (text, primary key) - Name of ETL stream (e.g., "invoices", "receipts", "sales-lines")
- last_date (date, optional) - Last processed date
- last_key (text, optional) - Last processed key
- updated_at (timestamp) - Last update timestamp

**Example Data**:
```
stream_name: "invoices"
last_date: "2025-10-15"
last_key: "INV-2025-001"
updated_at: "2025-10-16 10:30:00"
```

---

### Table: etl_logs

**Purpose**: Audit trail of ETL executions for monitoring and debugging.

**Columns**:
- id (bigserial, primary key) - Auto-incrementing log ID
- stream_name (text, optional) - ETL stream name
- run_at (timestamp) - Execution timestamp
- rows (integer, optional) - Number of rows processed
- status (text, optional) - Status: "ok" or "error"
- error (text, optional) - Error message if status is "error"

**Example Data**:
```
id: 1234
stream_name: "sales-lines"
run_at: "2025-10-16 10:30:00"
rows: 930
status: "ok"
error: NULL
```

---

## RELATIONSHIPS SUMMARY

### Primary Relationships

1. **fact_invoice → dim_customer** (Many-to-One)
   - Many invoices belong to one customer
   - Foreign key: customer_id

2. **fact_invoice → dim_salesperson** (Many-to-One)
   - Many invoices belong to one salesperson
   - Foreign key: sp_id (optional)

3. **fact_invoice_line → fact_invoice** (Many-to-One)
   - Many lines belong to one invoice
   - Foreign key: invoice_id
   - Cascade delete

4. **fact_invoice_line → dim_item** (Many-to-One)
   - Many lines reference one item
   - Foreign key: sku_id (optional)

5. **fact_receipt → dim_customer** (Many-to-One)
   - Many receipts belong to one customer
   - Foreign key: customer_id

6. **dim_item → dim_stock_group** (Many-to-One)
   - Many items belong to one stock group
   - Relationship via parent_name field

### Data Flow

```
Tally ERP → XML Export → Parser → Staging Tables → Fact Tables
                                      ↓
                                   Dimension Tables
```

---

## COMMON QUERY PATTERNS

### Pattern 1: Sales by Customer
```sql
SELECT 
  dc.name as customer,
  COUNT(DISTINCT fi.invoice_id) as invoice_count,
  SUM(fi.total) as total_sales
FROM fact_invoice fi
JOIN dim_customer dc ON dc.customer_id = fi.customer_id
WHERE fi.date BETWEEN '2025-09-01' AND '2025-09-30'
GROUP BY dc.name
ORDER BY total_sales DESC;
```

### Pattern 2: Line-Level Sales Details
```sql
SELECT 
  fi.date,
  fi.voucher_key,
  dc.name as customer,
  fil.sku_name,
  fil.qty,
  fil.uom,
  fil.rate,
  fil.line_total
FROM fact_invoice fi
JOIN fact_invoice_line fil ON fil.invoice_id = fi.invoice_id
LEFT JOIN dim_customer dc ON dc.customer_id = fi.customer_id
WHERE fi.date BETWEEN '2025-09-01' AND '2025-09-30'
ORDER BY fi.date DESC, fi.voucher_key;
```

### Pattern 3: Top Selling Items
```sql
SELECT 
  fil.sku_name,
  SUM(fil.qty) as total_qty,
  SUM(fil.line_total) as total_revenue
FROM fact_invoice_line fil
JOIN fact_invoice fi ON fi.invoice_id = fil.invoice_id
WHERE fi.date BETWEEN '2025-09-01' AND '2025-09-30'
GROUP BY fil.sku_name
ORDER BY total_revenue DESC
LIMIT 20;
```

---

## IMPORTANT NOTES FOR AI

### Data Types
- **text**: Variable-length strings, used for IDs and names
- **numeric(14,2)**: Decimal numbers with 14 total digits, 2 after decimal (for amounts)
- **numeric(14,3)**: Decimal numbers with 14 total digits, 3 after decimal (for quantities)
- **date**: ISO date format (YYYY-MM-DD)
- **timestamptz**: Timezone-aware timestamp
- **bigserial**: Auto-incrementing 64-bit integer

### Nullability
- Primary keys are NEVER null
- Foreign keys CAN be null (optional relationships)
- Most dimension fields are optional
- Fact table amounts are required

### Key Naming Conventions
- Primary keys: Usually match table name + "_id"
- Foreign keys: Usually named after referenced table + "_id"
- Timestamps: Usually end with "_at"

### Business Logic
- Invoices have multiple line items (1:N relationship)
- Tax is allocated proportionally to line items
- Line items reference both invoice and item
- Customer can have multiple invoices and receipts
- Items can appear on multiple invoices

### ETL Process
1. Data extracted from Tally ERP as XML
2. Parsed and loaded into staging tables
3. Staging tables used to upsert fact tables
4. Staging tables truncated after each batch
5. Checkpoints track last processed date
6. Logs record all ETL executions

### Common Mistakes to Avoid
- Don't forget to join fact_invoice_line with fact_invoice to get invoice details
- Don't assume all invoices have line items (check for NULL)
- Don't assume all items are in dim_item (sku_id can be NULL)
- Don't forget to filter by date range for performance
- Don't use staging tables in production queries (they're temporary)

---

## SCHEMA VERSION

This schema represents the final state after all migrations:
- 0001_cdm.sql - Initial schema
- 0002_add_vchtype.sql - Added voucher type
- 0003_dim_pincode.sql - Added pincode dimension
- 0004_stock_masters.sql - Added stock groups and extended items
- 0005_brand_flag.sql - Added brand flag
- 0006_fact_invoice_line.sql - Added line-level details

Total Tables: 16
- Dimensions: 6
- Facts: 3
- Staging: 2
- Operational: 2
- Other: 3 (including indexes and constraints)


