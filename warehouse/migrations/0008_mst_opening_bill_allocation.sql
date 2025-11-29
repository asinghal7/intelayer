-- Create mst_opening_bill_allocation table
-- Purpose: Store opening bill allocations per ledger sourced from Tally masters
-- Integration: Non-destructive, re-runnable migration consistent with existing warehouse DDL

create table if not exists mst_opening_bill_allocation (
  id bigserial primary key,
  ledger text not null,
  name text not null,
  bill_date date,
  opening_balance numeric(14,2) default 0,
  bill_credit_period int,
  is_advance boolean,
  created_at timestamptz default now()
);

create index if not exists idx_mst_opening_bill_alloc_ledger on mst_opening_bill_allocation(ledger);
create index if not exists idx_mst_opening_bill_alloc_name on mst_opening_bill_allocation(name);
create index if not exists idx_mst_opening_bill_alloc_bill_date on mst_opening_bill_allocation(bill_date);




