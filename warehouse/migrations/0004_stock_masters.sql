-- Stock group hierarchy (authoritative)
create table if not exists dim_stock_group (
  stock_group_id bigserial primary key,
  guid           text unique,
  name           text not null unique,
  parent_name    text,
  alter_id       bigint,
  updated_at     timestamptz default now()
);

create index if not exists idx_dim_stock_group_parent on dim_stock_group(parent_name);

-- Units catalog from dependent masters
create table if not exists dim_uom (
  uom_name       text primary key,
  original_name  text,
  gst_rep_uom    text,
  is_simple      boolean,
  alter_id       bigint,
  updated_at     timestamptz default now()
);

-- Extend existing dim_item table to support stock master hierarchy
alter table dim_item 
  add column if not exists guid text unique,
  add column if not exists parent_name text,  -- link to stock group
  add column if not exists updated_at timestamptz default now();

create index if not exists idx_dim_item_parent on dim_item(parent_name);
create index if not exists idx_dim_item_brand on dim_item(brand);

