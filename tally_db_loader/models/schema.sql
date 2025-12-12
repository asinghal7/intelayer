-- =============================================================================
-- Tally Database Loader - PostgreSQL Schema
-- =============================================================================
-- This schema mirrors the structure of Tally data for comprehensive sync.
-- All tables are created in the 'tally_db' schema to isolate from other data.
-- =============================================================================

-- Create dedicated schema
CREATE SCHEMA IF NOT EXISTS tally_db;

-- =============================================================================
-- SYNC METADATA TABLES
-- =============================================================================

-- Track sync checkpoints for incremental updates
CREATE TABLE IF NOT EXISTS tally_db.sync_checkpoint (
    entity_name TEXT PRIMARY KEY,
    last_alter_id BIGINT,
    last_sync_at TIMESTAMPTZ DEFAULT NOW(),
    row_count BIGINT DEFAULT 0,
    status TEXT DEFAULT 'pending',
    error_message TEXT
);

-- Log sync operations
CREATE TABLE IF NOT EXISTS tally_db.sync_log (
    id BIGSERIAL PRIMARY KEY,
    sync_type TEXT NOT NULL,  -- 'full', 'incremental', 'selective'
    entity_name TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    rows_processed BIGINT DEFAULT 0,
    rows_inserted BIGINT DEFAULT 0,
    rows_updated BIGINT DEFAULT 0,
    status TEXT DEFAULT 'running',
    error_message TEXT,
    duration_seconds NUMERIC(10, 2)
);

-- =============================================================================
-- COMPANY MASTER
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_company (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    name TEXT NOT NULL,
    formal_name TEXT,
    address TEXT,
    state TEXT,
    country TEXT,
    pincode TEXT,
    email TEXT,
    phone TEXT,
    website TEXT,
    currency_name TEXT,
    currency_symbol TEXT,
    financial_year_from DATE,
    financial_year_to DATE,
    books_from DATE,
    is_security_on BOOLEAN DEFAULT FALSE,
    is_tally_audit_on BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- LEDGER GROUP MASTER
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_group (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    name TEXT NOT NULL,
    name_lower TEXT,  -- For case-insensitive lookups
    parent TEXT,
    parent_lower TEXT,
    primary_group TEXT,  -- Ultimate parent in hierarchy
    is_revenue BOOLEAN DEFAULT FALSE,
    is_deemed_positive BOOLEAN DEFAULT FALSE,
    is_subledger BOOLEAN DEFAULT FALSE,
    affects_gross_profit BOOLEAN DEFAULT FALSE,
    sort_position SMALLINT,
    nature_of_group TEXT,  -- Assets, Liabilities, Income, Expenses
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mst_group_name ON tally_db.mst_group(name_lower);
CREATE INDEX IF NOT EXISTS idx_mst_group_parent ON tally_db.mst_group(parent_lower);

-- =============================================================================
-- LEDGER MASTER
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_ledger (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    name TEXT NOT NULL,
    name_lower TEXT,
    parent TEXT,
    parent_lower TEXT,
    primary_group TEXT,
    
    -- Classification
    is_revenue BOOLEAN DEFAULT FALSE,
    is_deemed_positive BOOLEAN DEFAULT FALSE,
    is_bill_wise_on BOOLEAN DEFAULT FALSE,
    is_cost_centres_on BOOLEAN DEFAULT FALSE,
    
    -- Opening balance
    opening_balance NUMERIC(17, 2) DEFAULT 0,
    closing_balance NUMERIC(17, 2) DEFAULT 0,
    
    -- GST details
    gstin TEXT,
    gst_registration_type TEXT,
    party_gstin TEXT,
    state_name TEXT,
    country_name TEXT,
    
    -- Contact details
    address TEXT,
    pincode TEXT,
    email TEXT,
    phone TEXT,
    contact_person TEXT,
    
    -- Banking details
    bank_name TEXT,
    bank_branch TEXT,
    bank_account_number TEXT,
    bank_ifsc TEXT,
    
    -- Credit terms
    credit_period INTEGER,  -- days
    credit_limit NUMERIC(17, 2),
    
    -- Tax details
    pan TEXT,
    income_tax_number TEXT,
    tds_applicable BOOLEAN DEFAULT FALSE,
    tcs_applicable BOOLEAN DEFAULT FALSE,
    
    -- Mailing details
    mailing_name TEXT,
    mailing_address TEXT,
    mailing_state TEXT,
    mailing_country TEXT,
    mailing_pincode TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mst_ledger_name ON tally_db.mst_ledger(name_lower);
CREATE INDEX IF NOT EXISTS idx_mst_ledger_parent ON tally_db.mst_ledger(parent_lower);
CREATE INDEX IF NOT EXISTS idx_mst_ledger_gstin ON tally_db.mst_ledger(gstin);
CREATE INDEX IF NOT EXISTS idx_mst_ledger_primary_group ON tally_db.mst_ledger(primary_group);

-- =============================================================================
-- STOCK GROUP MASTER
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_stock_group (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    name TEXT NOT NULL,
    name_lower TEXT,
    parent TEXT,
    parent_lower TEXT,
    is_add_able BOOLEAN DEFAULT TRUE,
    base_units TEXT,
    gst_applicable TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mst_stock_group_name ON tally_db.mst_stock_group(name_lower);
CREATE INDEX IF NOT EXISTS idx_mst_stock_group_parent ON tally_db.mst_stock_group(parent_lower);

-- =============================================================================
-- STOCK CATEGORY MASTER
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_stock_category (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    name TEXT NOT NULL,
    name_lower TEXT,
    parent TEXT,
    parent_lower TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mst_stock_category_name ON tally_db.mst_stock_category(name_lower);

-- =============================================================================
-- UNIT OF MEASUREMENT MASTER
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_unit (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    name TEXT NOT NULL,
    name_lower TEXT,
    original_name TEXT,
    is_simple_unit BOOLEAN DEFAULT TRUE,
    base_units TEXT,
    additional_units TEXT,
    conversion NUMERIC(17, 4),
    decimal_places SMALLINT DEFAULT 2,
    is_gst_excluded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mst_unit_name ON tally_db.mst_unit(name_lower);

-- =============================================================================
-- GODOWN (WAREHOUSE) MASTER
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_godown (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    name TEXT NOT NULL,
    name_lower TEXT,
    parent TEXT,
    parent_lower TEXT,
    address TEXT,
    is_internal BOOLEAN DEFAULT FALSE,
    has_no_space BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mst_godown_name ON tally_db.mst_godown(name_lower);

-- =============================================================================
-- STOCK ITEM MASTER
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_stock_item (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    name TEXT NOT NULL,
    name_lower TEXT,
    parent TEXT,  -- Stock group
    parent_lower TEXT,
    category TEXT,
    category_lower TEXT,
    base_units TEXT,
    
    -- Identification
    alias TEXT,
    part_number TEXT,
    hsn_code TEXT,
    description TEXT,
    narration TEXT,
    
    -- Stock details
    opening_balance NUMERIC(17, 4) DEFAULT 0,
    opening_value NUMERIC(17, 2) DEFAULT 0,
    opening_rate NUMERIC(17, 4) DEFAULT 0,
    closing_balance NUMERIC(17, 4) DEFAULT 0,
    closing_value NUMERIC(17, 2) DEFAULT 0,
    closing_rate NUMERIC(17, 4) DEFAULT 0,
    
    -- Pricing
    standard_cost NUMERIC(17, 4),
    standard_price NUMERIC(17, 4),
    
    -- GST
    gst_applicable TEXT,
    gst_type_of_supply TEXT,
    is_reverse_charge_applicable BOOLEAN DEFAULT FALSE,
    
    -- Classification
    is_batch_wise_on BOOLEAN DEFAULT FALSE,
    is_perishable_on BOOLEAN DEFAULT FALSE,
    is_expiry_on BOOLEAN DEFAULT FALSE,
    
    -- Costing
    costing_method TEXT,  -- FIFO, LIFO, WAC, etc.
    valuation_method TEXT,
    
    -- Additional
    ignore_negative_stock BOOLEAN DEFAULT FALSE,
    ignore_physical_difference BOOLEAN DEFAULT FALSE,
    treat_sales_as_manufactured BOOLEAN DEFAULT FALSE,
    treat_purchases_as_consumed BOOLEAN DEFAULT FALSE,
    treat_rejects_as_scrap BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mst_stock_item_name ON tally_db.mst_stock_item(name_lower);
CREATE INDEX IF NOT EXISTS idx_mst_stock_item_parent ON tally_db.mst_stock_item(parent_lower);
CREATE INDEX IF NOT EXISTS idx_mst_stock_item_hsn ON tally_db.mst_stock_item(hsn_code);

-- =============================================================================
-- COST CATEGORY MASTER
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_cost_category (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    name TEXT NOT NULL,
    name_lower TEXT,
    allocate_revenue BOOLEAN DEFAULT FALSE,
    allocate_non_revenue BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mst_cost_category_name ON tally_db.mst_cost_category(name_lower);

-- =============================================================================
-- COST CENTRE MASTER
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_cost_centre (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    name TEXT NOT NULL,
    name_lower TEXT,
    parent TEXT,
    parent_lower TEXT,
    category TEXT,
    category_lower TEXT,
    is_revenue BOOLEAN DEFAULT TRUE,
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mst_cost_centre_name ON tally_db.mst_cost_centre(name_lower);
CREATE INDEX IF NOT EXISTS idx_mst_cost_centre_category ON tally_db.mst_cost_centre(category_lower);

-- =============================================================================
-- VOUCHER TYPE MASTER
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_voucher_type (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    name TEXT NOT NULL,
    name_lower TEXT,
    parent TEXT,
    parent_lower TEXT,
    numbering_method TEXT,
    is_deemed_positive BOOLEAN DEFAULT FALSE,
    affects_stock BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Classification
    is_invoice BOOLEAN DEFAULT FALSE,
    is_accounting_voucher BOOLEAN DEFAULT FALSE,
    is_inventory_voucher BOOLEAN DEFAULT FALSE,
    is_order_voucher BOOLEAN DEFAULT FALSE,
    
    -- Properties
    is_optional BOOLEAN DEFAULT FALSE,
    common_narration BOOLEAN DEFAULT FALSE,
    use_ref_voucher_date BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mst_voucher_type_name ON tally_db.mst_voucher_type(name_lower);
CREATE INDEX IF NOT EXISTS idx_mst_voucher_type_parent ON tally_db.mst_voucher_type(parent_lower);

-- =============================================================================
-- CURRENCY MASTER
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_currency (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    name TEXT NOT NULL,
    name_lower TEXT,
    original_name TEXT,
    iso_code TEXT,
    formal_name TEXT,
    symbol TEXT,
    suffix_symbol TEXT,
    decimal_places SMALLINT DEFAULT 2,
    decimal_symbol TEXT DEFAULT '.',
    in_millions BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mst_currency_name ON tally_db.mst_currency(name_lower);

-- =============================================================================
-- VOUCHER TRANSACTIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.trn_voucher (
    guid TEXT PRIMARY KEY,
    alter_id BIGINT,
    
    -- Voucher identification
    voucher_type TEXT NOT NULL,
    voucher_type_lower TEXT,
    voucher_number TEXT,
    reference_number TEXT,
    date DATE NOT NULL,
    reference_date DATE,
    
    -- Party details
    party_name TEXT,
    party_name_lower TEXT,
    party_gstin TEXT,
    place_of_supply TEXT,
    consignee_name TEXT,
    buyer_name TEXT,
    
    -- Amounts
    amount NUMERIC(17, 2) DEFAULT 0,
    
    -- GST details
    gst_registration_type TEXT,
    invoice_delivery_notes TEXT,
    invoice_order_number TEXT,
    invoice_order_date DATE,
    shipping_bill_number TEXT,
    shipping_date DATE,
    port_code TEXT,
    
    -- Classification
    is_invoice BOOLEAN DEFAULT FALSE,
    is_accounting_voucher BOOLEAN DEFAULT FALSE,
    is_inventory_voucher BOOLEAN DEFAULT FALSE,
    is_order_voucher BOOLEAN DEFAULT FALSE,
    is_cancelled BOOLEAN DEFAULT FALSE,
    is_optional BOOLEAN DEFAULT FALSE,
    is_posted BOOLEAN DEFAULT TRUE,
    
    -- Narration
    narration TEXT,
    
    -- Source/tracking
    master_id TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trn_voucher_date ON tally_db.trn_voucher(date);
CREATE INDEX IF NOT EXISTS idx_trn_voucher_type ON tally_db.trn_voucher(voucher_type_lower);
CREATE INDEX IF NOT EXISTS idx_trn_voucher_party ON tally_db.trn_voucher(party_name_lower);
CREATE INDEX IF NOT EXISTS idx_trn_voucher_number ON tally_db.trn_voucher(voucher_number);
CREATE INDEX IF NOT EXISTS idx_trn_voucher_alter_id ON tally_db.trn_voucher(alter_id);

-- =============================================================================
-- ACCOUNTING ENTRIES (LEDGER ENTRIES)
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.trn_accounting (
    id BIGSERIAL PRIMARY KEY,
    voucher_guid TEXT NOT NULL REFERENCES tally_db.trn_voucher(guid) ON DELETE CASCADE,
    
    -- Ledger details
    ledger TEXT NOT NULL,
    ledger_lower TEXT,
    parent TEXT,
    
    -- Amounts (following open source tally-database-loader structure)
    -- In Tally: negative amount = debit, positive amount = credit
    amount NUMERIC(17, 2) DEFAULT 0,           -- Original signed amount from Tally
    amount_debit NUMERIC(17, 2) DEFAULT 0,     -- Absolute debit amount (when amount < 0)
    amount_credit NUMERIC(17, 2) DEFAULT 0,    -- Absolute credit amount (when amount > 0)
    
    -- Classification
    is_party_ledger BOOLEAN DEFAULT FALSE,
    is_deemed_positive BOOLEAN DEFAULT FALSE,
    
    -- GST details
    gst_class TEXT,
    gst_tax_type TEXT,
    gst_rate_incl_cess NUMERIC(10, 2),
    
    -- Additional
    narration TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trn_accounting_voucher ON tally_db.trn_accounting(voucher_guid);
CREATE INDEX IF NOT EXISTS idx_trn_accounting_ledger ON tally_db.trn_accounting(ledger_lower);

-- =============================================================================
-- INVENTORY ENTRIES
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.trn_inventory (
    id BIGSERIAL PRIMARY KEY,
    voucher_guid TEXT NOT NULL REFERENCES tally_db.trn_voucher(guid) ON DELETE CASCADE,
    
    -- Stock item
    stock_item TEXT NOT NULL,
    stock_item_lower TEXT,
    
    -- Godown
    godown TEXT,
    godown_lower TEXT,
    
    -- Tracking
    tracking_number TEXT,
    order_number TEXT,
    order_due_date DATE,
    
    -- Quantity and rate
    billed_qty NUMERIC(17, 4) DEFAULT 0,
    actual_qty NUMERIC(17, 4) DEFAULT 0,
    rate NUMERIC(17, 4) DEFAULT 0,
    amount NUMERIC(17, 2) DEFAULT 0,
    discount NUMERIC(17, 2) DEFAULT 0,
    
    -- Batch
    batch_name TEXT,
    
    -- Additional
    narration TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trn_inventory_voucher ON tally_db.trn_inventory(voucher_guid);
CREATE INDEX IF NOT EXISTS idx_trn_inventory_stock_item ON tally_db.trn_inventory(stock_item_lower);
CREATE INDEX IF NOT EXISTS idx_trn_inventory_godown ON tally_db.trn_inventory(godown_lower);

-- =============================================================================
-- BILL ALLOCATIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.trn_bill (
    id BIGSERIAL PRIMARY KEY,
    voucher_guid TEXT NOT NULL REFERENCES tally_db.trn_voucher(guid) ON DELETE CASCADE,
    
    -- Ledger for bill
    ledger TEXT NOT NULL,
    ledger_lower TEXT,
    
    -- Bill details
    name TEXT NOT NULL,  -- Bill reference name
    bill_type TEXT,  -- 'New Ref', 'Agst Ref', 'Advance', 'On Account'
    amount NUMERIC(17, 2) DEFAULT 0,
    bill_credit_period INTEGER,  -- days
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trn_bill_voucher ON tally_db.trn_bill(voucher_guid);
CREATE INDEX IF NOT EXISTS idx_trn_bill_ledger ON tally_db.trn_bill(ledger_lower);
CREATE INDEX IF NOT EXISTS idx_trn_bill_name ON tally_db.trn_bill(name);

-- =============================================================================
-- COST CENTRE ALLOCATIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.trn_cost_centre (
    id BIGSERIAL PRIMARY KEY,
    voucher_guid TEXT NOT NULL REFERENCES tally_db.trn_voucher(guid) ON DELETE CASCADE,
    accounting_id BIGINT REFERENCES tally_db.trn_accounting(id) ON DELETE CASCADE,
    
    -- Cost centre details
    cost_centre TEXT NOT NULL,
    cost_centre_lower TEXT,
    category TEXT,
    category_lower TEXT,
    
    -- Amount
    amount NUMERIC(17, 2) DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trn_cost_centre_voucher ON tally_db.trn_cost_centre(voucher_guid);
CREATE INDEX IF NOT EXISTS idx_trn_cost_centre_name ON tally_db.trn_cost_centre(cost_centre_lower);

-- =============================================================================
-- BATCH ALLOCATIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.trn_batch (
    id BIGSERIAL PRIMARY KEY,
    voucher_guid TEXT NOT NULL REFERENCES tally_db.trn_voucher(guid) ON DELETE CASCADE,
    inventory_id BIGINT REFERENCES tally_db.trn_inventory(id) ON DELETE CASCADE,
    
    -- Stock item and godown
    stock_item TEXT NOT NULL,
    stock_item_lower TEXT,
    godown TEXT,
    godown_lower TEXT,
    
    -- Batch details
    batch_name TEXT NOT NULL,
    manufacturing_date DATE,
    expiry_date DATE,
    
    -- Quantity
    billed_qty NUMERIC(17, 4) DEFAULT 0,
    actual_qty NUMERIC(17, 4) DEFAULT 0,
    amount NUMERIC(17, 2) DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trn_batch_voucher ON tally_db.trn_batch(voucher_guid);
CREATE INDEX IF NOT EXISTS idx_trn_batch_stock_item ON tally_db.trn_batch(stock_item_lower);
CREATE INDEX IF NOT EXISTS idx_trn_batch_name ON tally_db.trn_batch(batch_name);

-- =============================================================================
-- CLOSING STOCK
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.trn_closing_stock (
    id BIGSERIAL PRIMARY KEY,
    as_of_date DATE NOT NULL,
    stock_item TEXT NOT NULL,
    stock_item_lower TEXT,
    godown TEXT,
    godown_lower TEXT,
    
    -- Quantities
    closing_qty NUMERIC(17, 4) DEFAULT 0,
    closing_value NUMERIC(17, 2) DEFAULT 0,
    closing_rate NUMERIC(17, 4) DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(as_of_date, stock_item, godown)
);

CREATE INDEX IF NOT EXISTS idx_trn_closing_stock_date ON tally_db.trn_closing_stock(as_of_date);
CREATE INDEX IF NOT EXISTS idx_trn_closing_stock_item ON tally_db.trn_closing_stock(stock_item_lower);

-- =============================================================================
-- OPENING BILL ALLOCATIONS (from ledger masters)
-- =============================================================================

CREATE TABLE IF NOT EXISTS tally_db.mst_opening_bill (
    id BIGSERIAL PRIMARY KEY,
    ledger TEXT NOT NULL,
    ledger_lower TEXT,
    name TEXT NOT NULL,
    bill_date DATE,
    opening_balance NUMERIC(17, 2) DEFAULT 0,
    bill_credit_period INTEGER,
    is_advance BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(ledger, name)
);

-- Add updated_at column if it doesn't exist (for existing tables)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'tally_db' 
        AND table_name = 'mst_opening_bill' 
        AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE tally_db.mst_opening_bill ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_mst_opening_bill_ledger ON tally_db.mst_opening_bill(ledger_lower);
CREATE INDEX IF NOT EXISTS idx_mst_opening_bill_name ON tally_db.mst_opening_bill(name);

-- =============================================================================
-- MIGRATION: Add amount_debit/amount_credit to trn_accounting (for existing databases)
-- Following open source tally-database-loader structure
-- =============================================================================
DO $$
BEGIN
    -- Add amount_debit column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'tally_db' 
        AND table_name = 'trn_accounting' 
        AND column_name = 'amount_debit'
    ) THEN
        ALTER TABLE tally_db.trn_accounting ADD COLUMN amount_debit NUMERIC(17, 2) DEFAULT 0;
    END IF;
    
    -- Add amount_credit column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'tally_db' 
        AND table_name = 'trn_accounting' 
        AND column_name = 'amount_credit'
    ) THEN
        ALTER TABLE tally_db.trn_accounting ADD COLUMN amount_credit NUMERIC(17, 2) DEFAULT 0;
    END IF;
END $$;

-- Backfill existing records: derive debit/credit from signed amount
-- In Tally: negative amount = debit, positive amount = credit
UPDATE tally_db.trn_accounting
SET 
    amount_debit = CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END,
    amount_credit = CASE WHEN amount > 0 THEN amount ELSE 0 END
WHERE amount_debit = 0 AND amount_credit = 0 AND amount <> 0;

-- =============================================================================
-- COMPUTED VIEWS
-- =============================================================================

-- Drop existing views first to allow column type changes
DROP VIEW IF EXISTS tally_db.view_bills_outstanding CASCADE;

-- Outstanding bills view (combines opening and transaction bills)
-- Following open source tally-database-loader methodology for proper original_amount tracking
-- 
-- Key concepts:
-- 1. "New Ref" bills in transactions = original invoice amount (this IS the original)
-- 2. "Opening" bills from mst_opening_bill = remaining balance at period start
--    To get original: opening_balance + total adjustments made to this bill
-- 3. "Agst Ref" bills = payments/adjustments against the original bill
-- 4. "Advance" = advance payment (tracked separately)
--
CREATE OR REPLACE VIEW tally_db.view_bills_outstanding AS
WITH bill_movements AS (
    -- Opening bills (remaining balance from previous periods)
    SELECT
        ledger,
        name,
        bill_date AS date,
        opening_balance AS amount,
        'Opening' AS bill_type,
        bill_credit_period,
        is_advance,
        NULL::NUMERIC(17,2) AS new_ref_amount  -- Opening doesn't have original, will be calculated
    FROM tally_db.mst_opening_bill
    WHERE opening_balance IS NOT NULL AND opening_balance <> 0
    
    UNION ALL
    
    -- Transaction bills
    SELECT
        b.ledger,
        b.name,
        v.date,
        b.amount,
        b.bill_type,
        b.bill_credit_period,
        FALSE AS is_advance,
        -- For "New Ref", the amount IS the original invoice amount
        CASE WHEN b.bill_type = 'New Ref' THEN ABS(b.amount) ELSE NULL END AS new_ref_amount
    FROM tally_db.trn_bill b
    JOIN tally_db.trn_voucher v ON v.guid = b.voucher_guid
    WHERE b.name IS NOT NULL AND b.name <> ''
),
bill_summary AS (
    SELECT
        ledger,
        name,
        -- Bill date: earliest date when bill was created (from New Ref or Opening)
        MIN(CASE WHEN bill_type IN ('New Ref', 'Opening') THEN date END) AS bill_date,
        -- Credit period from bill metadata
        MAX(bill_credit_period) AS credit_period,
        -- Whether any entry is an advance
        BOOL_OR(is_advance) AS is_advance,
        -- Opening balance (from mst_opening_bill)
        SUM(CASE WHEN bill_type = 'Opening' THEN amount ELSE 0 END) AS opening_balance,
        -- New bills created in current period (New Ref)
        SUM(CASE WHEN bill_type = 'New Ref' THEN amount ELSE 0 END) AS new_ref_total,
        -- Advances
        SUM(CASE WHEN bill_type = 'Advance' THEN amount ELSE 0 END) AS advance_total,
        -- Total adjustments made (Agst Ref - these reduce the outstanding)
        SUM(CASE WHEN bill_type = 'Agst Ref' THEN amount ELSE 0 END) AS adjusted_total,
        -- Original amount from "New Ref" transactions (this IS the original invoice amount)
        MAX(new_ref_amount) AS tracked_original,
        -- Latest adjustment date
        MAX(CASE WHEN bill_type = 'Agst Ref' THEN date END) AS last_adjusted_date
    FROM bill_movements
    GROUP BY ledger, name
)
SELECT
    ledger,
    name AS bill_name,
    bill_date,
    -- Due date calculation
    CASE 
        WHEN bill_date IS NOT NULL AND credit_period > 0 
        THEN (bill_date + (credit_period || ' days')::INTERVAL)::DATE
        ELSE NULL
    END AS due_date,
    -- Original Amount Logic:
    -- 1. If we have a "New Ref" entry, use that as original (most accurate)
    -- 2. If only "Opening", reconstruct: opening_balance + |adjusted_total|
    --    (because opening is what's left after prior adjustments)
    COALESCE(
        tracked_original,  -- Original from "New Ref" if available
        ABS(opening_balance) + ABS(adjusted_total)  -- Reconstruct from opening + adjustments
    )::NUMERIC(17,2) AS original_amount,
    -- Total amount adjusted so far
    ABS(adjusted_total)::NUMERIC(17,2) AS adjusted_amount,
    -- Pending amount = opening + new_ref + advance + adjusted (adjusted is typically negative/opposite sign)
    ABS(opening_balance + new_ref_total + advance_total + adjusted_total)::NUMERIC(17,2) AS pending_amount,
    is_advance,
    last_adjusted_date
FROM bill_summary
-- Only show bills with non-zero pending balance
WHERE ABS(opening_balance + new_ref_total + advance_total + adjusted_total) > 0.01;

-- Drop existing views first to allow column type changes
DROP VIEW IF EXISTS tally_db.view_ledger_balance CASCADE;
DROP VIEW IF EXISTS tally_db.view_ledger_opening_balance CASCADE;

-- View to aggregate opening balances from bill allocations per ledger
-- This provides accurate opening balances derived from individual bill records
CREATE OR REPLACE VIEW tally_db.view_ledger_opening_balance AS
SELECT
    ob.ledger,
    LOWER(ob.ledger) AS ledger_lower,
    SUM(ob.opening_balance)::NUMERIC(17,2) AS opening_balance_from_bills,
    COUNT(*) AS bill_count
FROM tally_db.mst_opening_bill ob
GROUP BY ob.ledger;

-- Ledger balance view (uses opening balance from bill allocations when available)
-- Falls back to ledger's opening_balance if no bill allocations exist
-- Following open source tally-database-loader approach with separate debit/credit columns
CREATE OR REPLACE VIEW tally_db.view_ledger_balance AS
SELECT
    l.name AS ledger,
    l.parent AS group_name,
    l.primary_group,
    -- Use opening balance from bill allocations if available, else use ledger's opening_balance
    COALESCE(ob.opening_balance_from_bills, l.opening_balance, 0)::NUMERIC(17,2) AS opening_balance,
    l.opening_balance AS ledger_opening_balance,
    ob.opening_balance_from_bills AS bills_opening_balance,
    -- Total Debit: sum of all debit amounts (positive values in amount_debit column)
    COALESCE(SUM(a.amount_debit), 0)::NUMERIC(17,2) AS total_debit,
    -- Total Credit: sum of all credit amounts (positive values in amount_credit column)
    COALESCE(SUM(a.amount_credit), 0)::NUMERIC(17,2) AS total_credit,
    -- Net transaction total (credits - debits, using original signed amount)
    COALESCE(SUM(a.amount), 0)::NUMERIC(17,2) AS transaction_total,
    -- Closing balance = opening + transaction_total
    (COALESCE(ob.opening_balance_from_bills, l.opening_balance, 0) + COALESCE(SUM(a.amount), 0))::NUMERIC(17,2) AS closing_balance
FROM tally_db.mst_ledger l
LEFT JOIN tally_db.view_ledger_opening_balance ob ON ob.ledger_lower = l.name_lower
LEFT JOIN tally_db.trn_accounting a ON a.ledger_lower = l.name_lower
GROUP BY l.name, l.parent, l.primary_group, l.opening_balance, ob.opening_balance_from_bills;

-- Daily voucher summary view
CREATE OR REPLACE VIEW tally_db.view_daily_summary AS
SELECT
    date,
    voucher_type,
    COUNT(*) AS voucher_count,
    SUM(ABS(amount)) AS total_amount
FROM tally_db.trn_voucher
WHERE NOT is_cancelled
GROUP BY date, voucher_type
ORDER BY date DESC, voucher_type;

-- =============================================================================
-- AUDIT TRIGGERS (optional - for tracking changes)
-- =============================================================================

-- Function to update 'updated_at' timestamp
CREATE OR REPLACE FUNCTION tally_db.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to master tables
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'tally_db' AND tablename LIKE 'mst_%'
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS tr_update_updated_at ON tally_db.%I;
            CREATE TRIGGER tr_update_updated_at
            BEFORE UPDATE ON tally_db.%I
            FOR EACH ROW EXECUTE FUNCTION tally_db.update_updated_at();
        ', t, t);
    END LOOP;
END;
$$;

-- =============================================================================
-- GRANT PERMISSIONS (adjust as needed)
-- =============================================================================

-- Example: GRANT ALL ON ALL TABLES IN SCHEMA tally_db TO inteluser;
-- Example: GRANT USAGE ON SCHEMA tally_db TO inteluser;

