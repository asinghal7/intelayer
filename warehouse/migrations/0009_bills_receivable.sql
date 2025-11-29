-- Bills Receivable Implementation
-- Purpose: Staging table for transaction bill allocations and fact table for outstanding receivables
-- Integration: Non-destructive, re-runnable migration consistent with existing warehouse DDL

-- Staging table: captures bill allocations from vouchers
create table if not exists stg_trn_bill (
  id bigserial primary key,
  voucher_guid text not null,
  voucher_date date not null,
  ledger text not null,
  bill_name text not null,
  amount numeric(14,2) not null,
  billtype text,
  bill_credit_period int,
  created_at timestamptz default now()
);

create index if not exists idx_stg_trn_bill_voucher_guid on stg_trn_bill(voucher_guid);
create index if not exists idx_stg_trn_bill_ledger on stg_trn_bill(ledger);
create index if not exists idx_stg_trn_bill_voucher_date on stg_trn_bill(voucher_date);

-- Fact table: calculates outstanding bills receivable
-- Combines opening balances (mst_opening_bill_allocation) with transaction data (stg_trn_bill)
create table if not exists fact_bills_receivable (
  id bigserial primary key,
  ledger text not null,
  bill_name text not null,
  bill_date date,
  due_date date,
  original_amount numeric(14,2) default 0,
  adjusted_amount numeric(14,2) default 0,
  pending_amount numeric(14,2) default 0,
  billtype text,
  is_advance boolean,
  last_adjusted_date date,
  last_seen_at timestamptz default now(),
  unique(ledger, bill_name)
);

create index if not exists idx_fact_bills_receivable_ledger on fact_bills_receivable(ledger);
create index if not exists idx_fact_bills_receivable_bill_date on fact_bills_receivable(bill_date);
create index if not exists idx_fact_bills_receivable_due_date on fact_bills_receivable(due_date);
create index if not exists idx_fact_bills_receivable_pending on fact_bills_receivable(pending_amount) where pending_amount is not null;

