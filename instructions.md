
You are extending an existing Python + Postgres ETL that already syncs invoice-level customers from Tally over HTTP. 
Implement a minimal, SAFE Phase-1 stock-master using the *same codebase*, with **no breaking changes** to existing flows.

# Scope (Phase-1 only)
- Parse Tally’s **Masters export XML** (the same file produced by: Master → Stock Groups → Include dependent masters = Yes). 
- Ingest **Stock Groups** as the authoritative hierarchy; treat **root group** as “brand”.
- If the XML also contains **Stock Items**, ingest basic item fields (name, parent, units, HSN) to a dim table. If items are NOT present, just load groups now; we’ll add items via “List of Stock Items”/HTTP later.
- Load **Units** (dependent masters) for UOM mapping when present.
- Provide **two input modes**:
  1) `--from-file Master.xml` (use the uploaded XML)
  2) `--from-tally "<Company Name>"` (perform the HTTP Export call with built-in reports; still no TDL).
- Ship with **dry-run**, **preview**, and **validation SQL** so the user (me) can check & approve before we switch it on.

# Reuse
- Reuse existing DB adapter patterns (e.g., adapter.py) for connections/transactions/logs.
- Reuse CLI structure in run.py (add a new subcommand rather than editing current invoice commands).

# Files to add
1) sql/0002_stock_master_from_xml.sql
2) etl/stock_master_from_xml.py
3) Update run.py to register a `stockmaster` subcommand.
4) If needed, add lxml & requests to requirements.

# 1) sql/0002_stock_master_from_xml.sql
Create idempotent objects. Do not break existing facts. Use separate dim tables for clarity.

```sql
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

-- Optional: units catalog from dependent masters (if present)
create table if not exists dim_uom (
  uom_name       text primary key,
  original_name  text,
  gst_rep_uom    text,
  is_simple      boolean,
  alter_id       bigint,
  updated_at     timestamptz default now()
);

-- Basic SKU table for Phase-1 (only if you don’t already have a dim_item/dim_sku)
-- If you already have one, adapt the UPSERTs in the Python file to write there.
create table if not exists dim_sku (
  sku_id     bigserial primary key,
  guid       text unique,
  sku_name   text not null,
  parent_name text,
  uom        text,
  hsn        text,
  brand_name text,         -- computed = root stock group
  updated_at timestamptz default now(),
  unique (sku_name, parent_name)
);

create index if not exists idx_dim_sku_brand on dim_sku(brand_name);
````

# 2) etl/stock_master_from_xml.py

Requirements: lxml, requests (for live export), and your existing adapter for DB.

## Behavior

* CLI:

  * `python -m etl.stock_master_from_xml stockmaster --from-file Master.xml --dry-run --preview 50`
  * `python -m etl.stock_master_from_xml stockmaster --from-tally "Ashirvad Sales (23-24/24-25)" --preview 100`
  * Common flags: `--export-csv out.csv`
* Steps:

  1. Ensure schema `sql/0002_stock_master_from_xml.sql`.
  2. Obtain XML:

     * If `--from-file`, read local file.
     * If `--from-tally`, POST the “All Masters” (or “List of Stock Groups”) built-in export:

       * ReportName: `All Masters` OR `List of Stock Groups` (XML), with `<SVCURRENTCOMPANY>`.
  3. Parse:

     * **Units**: `<UNIT>` → NAME, ORIGINALNAME, GSTREPUOM, ISSIMPLEUNIT, ALTERID.
     * **Stock Groups**: `<STOCKGROUP>` → NAME, PARENT (empty/null for root), GUID, ALTERID.
     * **Stock Items** (if present): `<STOCKITEM>` → NAME, PARENT (immediate group), BASEUNITS, HSNCODE/HSNDETAILS (when present), GUID.
  4. Dry-run mode builds in-memory rows and prints counts + sample preview; real mode UPSERTs:

     * `dim_stock_group`: upsert by GUID (fallback name).
     * `dim_uom`: upsert by uom_name.
     * `dim_sku`: if items parsed, upsert by GUID (fallback sku_name + parent_name). Keep non-null existing values unless replaced with non-empty new values.
  5. Compute **brand_name** for every SKU by walking `dim_stock_group` upwards from `parent_name` until root.
  6. Preview: sample table (brand_name, sku_name, uom, hsn). Optionally CSV.

## UPSERT SQL (write exactly; use adapter’s parameterization)

-- Groups (GUID-first, fallback name)

```sql
insert into dim_stock_group (guid, name, parent_name, alter_id, updated_at)
values ($1,$2,$3,$4, now())
on conflict (guid) do update
  set name=excluded.name, parent_name=excluded.parent_name,
      alter_id=excluded.alter_id, updated_at=now();

insert into dim_stock_group (name, parent_name, alter_id, updated_at)
values ($1,$2,$3, now())
on conflict (name) do update
  set parent_name=excluded.parent_name, alter_id=excluded.alter_id, updated_at=now();
```

-- Units

```sql
insert into dim_uom (uom_name, original_name, gst_rep_uom, is_simple, alter_id, updated_at)
values ($1,$2,$3,$4,$5, now())
on conflict (uom_name) do update
  set original_name=excluded.original_name,
      gst_rep_uom=excluded.gst_rep_uom,
      is_simple=excluded.is_simple,
      alter_id=excluded.alter_id,
      updated_at=now();
```

-- SKUs (only if <STOCKITEM> exists in the XML)

```sql
insert into dim_sku (guid, sku_name, parent_name, uom, hsn, updated_at)
values ($1,$2,$3,$4,$5, now())
on conflict (guid) do update
  set sku_name=excluded.sku_name,
      parent_name=excluded.parent_name,
      uom = coalesce(nullif(excluded.uom,''), dim_sku.uom),
      hsn = coalesce(nullif(excluded.hsn,''), dim_sku.hsn),
      updated_at=now();

insert into dim_sku (sku_name, parent_name, uom, hsn, updated_at)
values ($1,$2,$3,$4, now())
on conflict (sku_name, parent_name) do update
  set uom = coalesce(nullif(excluded.uom,''), dim_sku.uom),
      hsn = coalesce(nullif(excluded.hsn,''), dim_sku.hsn),
      updated_at=now();
```

-- Compute brand = root group (works even with variable depths)

```sql
with recursive grp as (
  select s.sku_id, g.name as group_name, g.parent_name, 1 as depth
  from dim_sku s
  left join dim_stock_group g on g.name = s.parent_name
  union all
  select grp.sku_id, g2.name, g2.parent_name, grp.depth + 1
  from grp
  join dim_stock_group g2 on g2.name = grp.parent_name
),
root as (
  select sku_id,
         (array_agg(group_name order by case when parent_name is null then 0 else 1 end, depth asc))[1] as root_group
  from grp
  group by sku_id
)
update dim_sku s
set brand_name = coalesce(r.root_group, s.parent_name)
from root r
where r.sku_id = s.sku_id
  and coalesce(s.brand_name,'') <> coalesce(r.root_group, s.parent_name,'');
```

## Parser notes

* Map empty tags to NULL; `.text.strip()` where applicable.
* For **HSN**: prefer the latest `<HSNDETAILS.LIST>` with `<HSNCODE>` if multiple appear; else take first non-empty.
* For **UOM**: take `<BASEUNITS>` on item; if empty, try to map from `dim_uom` if name matches.
* GUID may be absent on some groups/items; the fallback uniqueness is `name` (groups) and `(sku_name, parent_name)` (items).

## Preview (interim check)

* When dry-run or after real run, show:

  * Counts: groups parsed, units parsed, items parsed; upserts (inserted/updated) if not dry-run.
  * If items present: a table of `brand_name, sku_name, uom, hsn` limited by `--preview N`.
  * If items NOT present: show **group tree** sample: root groups and a few children to verify hierarchy.

SQL helpers for me to review:

```sql
-- 1) Totals
select (select count(*) from dim_stock_group) as groups,
       (select count(*) from dim_uom) as uoms,
       (select count(*) from dim_sku) as skus,
       (select count(distinct brand_name) from dim_sku where brand_name is not null) as brands;

-- 2) Sample of SKUs (if present)
select brand_name, sku_name, uom, hsn
from dim_sku
order by brand_name nulls last, sku_name
limit 50;

-- 3) If no SKUs in XML, show a peek of group roots & children
select g.name as root, c.name as child
from dim_stock_group g
left join dim_stock_group c on c.parent_name = g.name
where g.parent_name is null
order by g.name, c.name
limit 50;
```

# 3) run.py integration

* Add a subcommand:

  * `python run.py stockmaster --from-file Master.xml --dry-run --preview 50`
  * `python run.py stockmaster --from-tally "Ashirvad Sales (23-24/24-25)" --preview 100`
* Delegate to `etl/stock_master_from_xml.py`.

# 4) Requirements

* Ensure these exist (add if missing):

  * lxml
  * requests

# Implementation constraints

* Keep functions small: `load_xml_file()`, `fetch_export_http(company)`, `parse_units()`, `parse_groups()`, `parse_items_if_any()`, `upsert_groups()`, `upsert_units()`, `upsert_items()`, `compute_brands()`, `preview()`.
* Clean logs, clear exceptions for malformed XML.
* No changes to existing invoice ingestion.
* Idempotent migrations and upserts.

# Final developer checklist (print at end of run)

* Show whether SKUs were found in the XML. If not, suggest running the live “List of Stock Items” export later.
* Show distinct count of root groups (brands).
* If any item parent group is missing in dim_stock_group, log the item and skip brand computation for that row.

```

---

### How we’ll validate together
1) Run: `python run.py stockmaster --from-file Master.xml --dry-run --preview 50`  
   Paste me the first ~10 rows of the preview (or the root/child group peek if no SKUs present).
2) If structure looks right, run without `--dry-run`, then share:
   - totals, distinct brand count, and a couple of known SKUs/brands for spot checks.
3) If any brand looks off, we’ll tweak the “brand = root” logic (e.g., pin a specific ancestor level for certain families).
```
