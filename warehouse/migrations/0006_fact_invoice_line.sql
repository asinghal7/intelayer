-- Fact lines table (create if missing)
create table if not exists fact_invoice_line (
  invoice_line_id bigserial primary key,
  invoice_id      text not null references fact_invoice(invoice_id) on delete cascade,
  sku_id          text,                -- nullable: resolve by dim_item.item_id if available
  sku_name        text,                -- denormalized item name as seen on voucher
  qty             numeric(14,3),
  uom             text,
  rate            numeric(14,2),
  discount        numeric(14,2),
  line_basic      numeric(14,2),       -- pre-tax (as emitted by InventoryEntries.Amount)
  line_tax        numeric(14,2),       -- allocated or direct if provided
  line_total      numeric(14,2),       -- basic + tax
  created_at      timestamptz default now()
);

create index if not exists idx_fil_invoice on fact_invoice_line (invoice_id);
create index if not exists idx_fil_sku on fact_invoice_line (sku_id);

-- Lightweight staging (only if you don't already stage lines)
create table if not exists stg_vreg_header (
  guid text,
  vch_no text,
  vch_date date,
  party text,
  basic_amount numeric(14,2),
  tax_amount numeric(14,2),
  total_amount numeric(14,2)
);

create table if not exists stg_vreg_line (
  voucher_guid text,
  stock_item_name text,
  billed_qty text,        -- e.g., "2 Nos"
  rate text,              -- e.g., "35000 / Nos"
  amount numeric(14,2),   -- line basic (pre-tax), as in your current parse
  discount numeric(14,2)  -- if present in your current parse; else null
);
