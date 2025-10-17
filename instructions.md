
You’re extending an existing Python + Postgres ETL that ALREADY fetches vouchers via Voucher Register and parses item-level details from each voucher (InventoryEntries). DO NOT introduce a new TDL or a different report. Reuse the current HTTP request & parsing logic that exists in the repo.

## Goal
Persist the item lines you already parse from Voucher Register into a new table `fact_invoice_line`, so we can answer “who bought which SKU” with (invoice_id, customer, item/SKU, qty, uom, rate, pre_tax, tax, total, date).

## Constraints
- Keep the existing headers flow (fact_invoice) as-is.
- Use the same date-range CLI and company settings you already support in `run.py`.
- Reuse DB helpers in `adapter.py`.
- If you already have any staging tables, use them; otherwise create light stg tables below.
- Avoid schema changes to existing tables unless adding safe indexes.

## Files to ADD
1) `sql/0003_fact_invoice_line.sql`
2) `etl/sales_lines_from_vreg.py`
3) Update `run.py` to add a subcommand: `sales-lines-from-vreg`

### 1) sql/0003_fact_invoice_line.sql
Idempotent migration only.

```sql
-- Fact lines table (create if missing)
create table if not exists fact_invoice_line (
  invoice_line_id bigserial primary key,
  invoice_id      bigint not null references fact_invoice(invoice_id) on delete cascade,
  sku_id          bigint,              -- nullable: resolve by dim_sku if available
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

-- Lightweight staging (only if you don’t already stage lines)
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
````

### 2) etl/sales_lines_from_vreg.py

Implement a module that:

* Imports/uses the **same** Voucher Register fetcher you already have (e.g., a function/class you call today).
* Hooks into the parsed object where you currently read: voucher.GUID, voucher.Date, voucher.VoucherNumber, voucher.PartyLedgerName, voucher.InventoryEntries (each with StockItemName, BilledQty, Rate, Amount, Discount if any), and voucher GST ledger totals (CGST/SGST/IGST) that your code already aggregates for header amounts.
* Supports:

  * `--lookback-days N` or `--from YYYY-MM-DD --to YYYY-MM-DD` (mirror your existing CLI)
  * `--dry-run`
  * `--preview N`
* Flow:

  1. **Run migration** `0003_fact_invoice_line.sql` if not yet applied.
  2. **Fetch vouchers** using the SAME function you use now (do not change request XML).
  3. **Stage** rows: truncate `stg_vreg_header` + `stg_vreg_line`, insert headers & lines parsed from your existing structures.
  4. **Upsert headers** into `fact_invoice` the same way you already do (or skip if you’re already doing it earlier in the pipeline).
  5. **Delete + insert lines per voucher**:

     * Find `invoice_id` by joining staged headers to `fact_invoice` on `(vch_no, vch_date)` or GUID (whichever your system uses).
     * Delete existing `fact_invoice_line` for those `invoice_id`s.
     * Insert line rows with:

       * `sku_id` resolved by `dim_sku`:

         * Preferred: by `guid` if your schema keeps it on dim_sku and your parser captures it.
         * Else fallback: `lower(dim_sku.sku_name) = lower(stock_item_name)`.
       * `qty` = numeric from `billed_qty` (regex on the numeric part).
       * `uom` = unit token from `billed_qty` OR from `rate` (after slash) when present.
       * `rate` = numeric part of `rate` before `/`.
       * `line_basic` = staged `amount`.
       * `line_tax` = proportional allocation from voucher tax, unless you already parse line tax (if you do, use your value).
       * `line_total` = `line_basic + line_tax`.
  6. **Preview**: print top N rows “who bought which SKU”.

Parsing helpers (keep tiny):

* `parse_qty_uom("2.00 Nos") -> (2.00, "Nos")`
* `parse_rate("35000 / Nos") -> 35000`
* If your current code already does these, REUSE those helpers instead of reimplementing.

**SQL used by this module (parameterized via adapter):**

Headers → (only if you need to upsert here; otherwise rely on your existing header loader)

```sql
insert into fact_invoice (vch_no, date, vchtype, customer_id, basic_amount, tax_amount, total)
select vch_no, vch_date, 'Invoice',
       coalesce(dc.customer_id, 0)::bigint,
       basic_amount, tax_amount, total_amount
from stg_vreg_header h
left join dim_customer dc on lower(dc.name) = lower(h.party)
on conflict (vch_no, date) do update
  set basic_amount = excluded.basic_amount,
      tax_amount   = excluded.tax_amount,
      total        = excluded.total;
```

Delete & reinsert lines:

```sql
with inv as (
  select fi.invoice_id, fi.vch_no, fi.date
  from fact_invoice fi
  join stg_vreg_header h on h.vch_no = fi.vch_no and h.vch_date = fi.date
),
line_src as (
  select
    i.invoice_id,
    l.stock_item_name,
    l.billed_qty,
    l.rate,
    l.amount as line_basic
  from stg_vreg_line l
  join stg_vreg_header h on h.guid = l.voucher_guid
  join inv i on i.vch_no = h.vch_no and i.date = h.vch_date
),
sum_basic as (
  select invoice_id, sum(line_basic) as sum_line_basic
  from line_src group by 1
),
tax_alloc as (
  select i.invoice_id, h.tax_amount as voucher_tax
  from stg_vreg_header h
  join inv i on i.vch_no = h.vch_no and i.date = h.vch_date
)
delete from fact_invoice_line fil
using inv
where fil.invoice_id = inv.invoice_id;

insert into fact_invoice_line (
  invoice_id, sku_id, sku_name, qty, uom, rate, discount, line_basic, line_tax, line_total
)
select
  ls.invoice_id,
  ds.sku_id,
  ls.stock_item_name,
  (regexp_matches(coalesce(ls.billed_qty,''), '([0-9.+-]+)[[:space:]]*([^/]*)'))[1]::numeric as qty,
  nullif((regexp_matches(coalesce(ls.billed_qty,''), '([0-9.+-]+)[[:space:]]*([^/]*)'))[2], '') as uom,
  nullif(regexp_replace(coalesce(ls.rate,''), '[/].*$', ''), '')::numeric as rate,
  null::numeric as discount,  -- set from your parser if available
  ls.line_basic,
  round(coalesce((ls.line_basic / nullif(sb.sum_line_basic,0)) * coalesce(ta.voucher_tax,0),0),2) as line_tax,
  round(ls.line_basic + coalesce((ls.line_basic / nullif(sb.sum_line_basic,0)) * coalesce(ta.voucher_tax,0),0),2) as line_total
from line_src ls
left join sum_basic sb on sb.invoice_id = ls.invoice_id
left join tax_alloc ta on ta.invoice_id = ls.invoice_id
left join dim_sku ds on lower(ds.sku_name) = lower(ls.stock_item_name);
```

**Preview query (print in the tool when `--preview` is set):**

```sql
select
  fi.date, fi.vch_no,
  dc.name as customer,
  fil.sku_name, fil.qty, fil.uom, fil.rate,
  fil.line_basic, fil.line_tax, fil.line_total
from fact_invoice fi
join fact_invoice_line fil on fil.invoice_id = fi.invoice_id
left join dim_customer dc on dc.customer_id = fi.customer_id
order by fi.date desc, fi.vch_no
limit %s;
```

### 3) run.py

Add a subcommand **without** modifying existing ones:

* `python run.py sales-lines-from-vreg --lookback-days 7 --dry-run --preview 25`
* `python run.py sales-lines-from-vreg --from 2025-04-01 --to 2025-10-15 --preview 50`

Behavior:

* Uses the same company/date-range options you already support for Voucher Register.
* If `--dry-run`: do fetch+parse+stage in memory and show the preview; skip DB writes.

## Validation & interim checks (print at end)

* Headers seen / staged; Lines staged; Invoices affected.
* Inserted/Updated header counts (if you upserted here).
* Lines inserted.
* `unmatched_skus_by_name` (count & sample of item names not found in dim_sku).
* `unmatched_customers` (if any).
* Reminder that we can switch to GUID-based SKU resolution later (if your current parse doesn’t carry item GUID).

## Notes

* Many Voucher Register exports emit `InventoryEntries.Amount` as **pre-tax**; your header tax is from GST ledgers. The proportional allocation above is the safest default. If your parser already extracts **line-level GST**, prefer those values and skip allocation.
* Returns/Credit Notes: if your Voucher Register includes them, add a `where vch_type = 'Sales'` filter in your existing fetch or exclude negatives when inserting lines (leave as you already do for headers).
* Performance: for large windows, chunk by 7 days; your existing runner likely already does this—reuse it.

Build all of the above now. Keep code small, plug into existing fetch/parsing path, and DO NOT change the request envelope or header ingestion that already works.

```

---

Run it like this to test without writing:

```

python run.py sales-lines-from-vreg --lookback-days 7 --dry-run --preview 20

```

Then run it “for real” (drop `--dry-run`) and share the preview/summary if you want me to sanity-check the results.
```
