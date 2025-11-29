-- Tally loader auxiliary tables to align with open-source schema.
-- Creates a dedicated schema to avoid clashing with existing tables.

create schema if not exists tally_loader;

-- View to expose existing opening balances in the expected structure.
create or replace view tally_loader.mst_opening_bill_allocation as
select
  ledger,
  coalesce(ledger, '') as _ledger,
  coalesce(opening_balance, 0)::numeric(17,4) as opening_balance,
  bill_date,
  coalesce(name, '') as name,
  coalesce(bill_credit_period, 0) as bill_credit_period,
  case when is_advance then 1 else 0 end as is_advance
from mst_opening_bill_allocation;

-- Voucher header table (subset of original schema).
create table if not exists tally_loader.trn_voucher (
  guid text primary key,
  alterid bigint,
  date date not null,
  voucher_type text,
  voucher_type_internal text,
  voucher_number text,
  reference_number text,
  reference_date date,
  narration text,
  party_name text,
  party_name_internal text,
  place_of_supply text,
  is_invoice boolean,
  is_accounting_voucher boolean,
  is_inventory_voucher boolean,
  is_order_voucher boolean,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_tally_loader_trn_voucher_date
  on tally_loader.trn_voucher(date);

-- Bill allocation table.
create table if not exists tally_loader.trn_bill (
  guid text not null,
  ledger text not null,
  ledger_internal text,
  name text not null,
  amount numeric(17,2) not null default 0,
  billtype text,
  bill_credit_period int,
  created_at timestamptz default now()
);

create index if not exists idx_tally_loader_trn_bill_guid
  on tally_loader.trn_bill(guid);

create index if not exists idx_tally_loader_trn_bill_ledger_name
  on tally_loader.trn_bill(ledger, name);




