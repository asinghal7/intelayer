# Stock Master – Usage Guide (Phase‑1)

This agent loads Stock Groups (brand hierarchy), Units (UOM), and Stock Items from Tally into Postgres, with optional brand filtering and clear/reload controls.

## Prerequisites
- TallyPrime HTTP server enabled (same LAN):
  - Enable HTTP Server = Yes; Port = your .env `TALLY_URL` port
  - Accept HTTP POST = Yes
- .env configured:
  - `TALLY_URL=http://<ip>:<port>`
  - `TALLY_COMPANY=Exact Company Name as in Tally`
  - `DB_URL=postgresql://inteluser:change_me@localhost:5432/intelayer`
- Docker Postgres (optional): `docker compose -f ops/docker-compose.yml up -d db`

## Commands

Dry‑run with preview (no DB writes):
```
python -m agent.stock_masters --from-tally --dry-run --preview 50
```

Filter to specific brands (roots and descendants):
```
python -m agent.stock_masters --from-tally \
  --brands "Whirlpool,Voltas,V-Guard Industries Ltd" \
  --dry-run --preview 50
```

Real load (writes to DB):
```
python -m agent.stock_masters --from-tally --preview 50
```

Export a CSV snapshot (after load or in dry‑run parse):
```
python -m agent.stock_masters --from-tally --export-csv masters.csv
```

### Clear / Reload controls

Clear and reload all brands:
```
python -m agent.stock_masters --from-tally --clear-reload
```

Clear and reload specific brands only:
```
python -m agent.stock_masters --from-tally \
  --brands "Whirlpool,Voltas" --clear-reload
```

Clear only (no reload):
```
python -m agent.stock_masters --from-tally --brands "Whirlpool" --clear-only
```

Dry‑run clear (shows rows to be deleted):
```
python -m agent.stock_masters --from-tally --brands "Whirlpool" --clear-reload --dry-run
```

## What it does
- Fetches masters from Tally using Export/Data:
  - All Masters (Stock Groups)
  - List of Accounts → AccountType=Units
  - List of Accounts → AccountType=Stock Items
- Parses and upserts into Postgres:
  - `dim_stock_group(name, parent_name, guid, alter_id, is_brand)`
  - `dim_uom(uom_name, original_name, gst_rep_uom, is_simple, alter_id)`
  - `dim_item(item_id, guid, name, parent_name, uom, hsn, brand)`
- Computes `brand` for items by walking group hierarchy to the root. Root groups are also flagged as `is_brand=true` (see migration 0005).

## Validation SQL
```
select count(*) from dim_stock_group;        -- groups
select count(*) from dim_uom;                -- units
select count(*) from dim_item;               -- items
select name from dim_stock_group where is_brand=true order by name limit 50; -- brands
select brand, count(*) from dim_item group by brand order by 2 desc;         -- items per brand
```

## Troubleshooting
- If Tally returns 0 rows:
  - Verify `TALLY_COMPANY` matches exactly
  - Ensure Tally HTTP server is reachable from your machine
  - Confirm the company has Stock Groups/Items defined
- If XML errors occur, the raw response may be written to `tally_masters_response.xml` for inspection.


