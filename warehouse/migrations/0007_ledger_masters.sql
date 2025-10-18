-- Migration 0007: Ledger Masters
-- Adds ledger group hierarchy and customer ledger group reference

-- Create dim_ledger_group table for ledger group hierarchy
create table if not exists dim_ledger_group (
  ledger_group_id  bigserial primary key,
  guid             text unique,
  name             text unique not null,
  parent_name      text,
  alter_id         bigint,
  updated_at       timestamptz default now()
);

-- Add ledger_group_name column to dim_customer
alter table dim_customer add column if not exists ledger_group_name text;

-- Create indexes for performance
create index if not exists idx_dim_ledger_group_guid on dim_ledger_group(guid);
create index if not exists idx_dim_ledger_group_parent on dim_ledger_group(parent_name);
create index if not exists idx_dim_customer_ledger_group on dim_customer(ledger_group_name);

-- Add comment for documentation
comment on table dim_ledger_group is 'Ledger group hierarchy from Tally (e.g., Sundry Debtors, Bank Accounts)';
comment on column dim_ledger_group.parent_name is 'Parent group name for hierarchy (NULL for root groups)';
comment on column dim_customer.ledger_group_name is 'Ledger group this customer belongs to (e.g., "Sundry Debtors", "North Zone Debtors")';

