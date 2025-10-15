-- Add brand flag to stock groups and backfill for roots
alter table dim_stock_group
  add column if not exists is_brand boolean default false;

-- Backfill: mark groups with NULL/empty parent as brands
update dim_stock_group
set is_brand = true
where coalesce(parent_name,'') = '';

-- Helpful index for brand queries
create index if not exists idx_dim_stock_group_is_brand on dim_stock_group(is_brand);

