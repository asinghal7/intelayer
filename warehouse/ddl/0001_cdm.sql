-- Dimensions
create table if not exists dim_customer (
  customer_id text primary key,
  name        text not null,
  gstin       text,
  city        text,
  pincode     text,
  created_at  timestamptz default now()
);

create table if not exists dim_item (
  item_id   text primary key,
  sku       text,
  name      text not null,
  brand     text,
  hsn       text,
  uom       text,
  created_at timestamptz default now()
);

create table if not exists dim_salesperson (
  sp_id     text primary key,
  name      text not null
);

-- Facts
create table if not exists fact_invoice (
  invoice_id  text primary key,
  voucher_key text unique,
  date        date not null,
  customer_id text references dim_customer(customer_id),
  sp_id       text references dim_salesperson(sp_id),
  subtotal    numeric not null,
  tax         numeric not null,
  total       numeric not null,
  roundoff    numeric default 0
);

create table if not exists fact_invoice_line (
  id         bigserial primary key,
  invoice_id text references fact_invoice(invoice_id),
  item_id    text references dim_item(item_id),
  qty        numeric not null,
  rate       numeric not null,
  line_total numeric not null,
  tax        numeric default 0
);

create table if not exists fact_receipt (
  id          bigserial primary key,
  receipt_key text unique,
  date        date not null,
  customer_id text references dim_customer(customer_id),
  amount      numeric not null
);

-- Ops
create table if not exists etl_checkpoints (
  stream_name text primary key,
  last_date   date,
  last_key    text,
  updated_at  timestamptz default now()
);

create table if not exists etl_logs (
  id          bigserial primary key,
  stream_name text,
  run_at      timestamptz default now(),
  rows        int,
  status      text,
  error       text
);

-- Indexes
create index if not exists idx_fact_invoice_date on fact_invoice(date);
create index if not exists idx_fact_invoice_customer on fact_invoice(customer_id);
create index if not exists idx_fact_receipt_date on fact_receipt(date);
create index if not exists idx_fact_line_item on fact_invoice_line(item_id);

