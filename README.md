# intelayer

Intelligent analytics layer for MSME ERPs — **Tally-first**. Extract via **HTTP/XML**, load to **Postgres** (CDM), visualize with **Metabase**. Adapter-ready (+other ERPs later), AI-ready.

## Quick start (uses your existing .venv)
1) Start infra (Postgres + Metabase):  
   `docker compose -f ops/docker-compose.yml up -d`
2) Copy env: `cp .env.example .env` and set `TALLY_URL`, `TALLY_COMPANY`, `DB_URL`.
3) Apply schema:  
   `psql $DB_URL -f warehouse/ddl/0001_cdm.sql`
4) Install deps into your existing venv:  
   `pip install -e .`
5) Run ETL once: `python agent/run.py`
6) **[Optional]** Load historical data: `python -m agent.backfill 2024-04-01 2024-10-13` (see `BACKFILL_QUICKSTART.md`)
7) Open Metabase: http://localhost:3000 (connect to Postgres).

## Structure
- `adapters/` — adapter SDK + Tally HTTP adapter
- `agent/` — ETL runner (incremental, idempotent)
- `warehouse/` — CDM DDL + migrations
- `dashboards/` — Metabase exports + KPI docs
- `ops/` — Docker Compose, backups, health checks
- `tests/` — sample XML + parser test

**Security**: Keep the Tally HTTP port LAN-only (Windows Firewall).  
**Trust-first**: Verify reconciliation (monthly totals) before relying on dashboards.

## Testing
- Install test tools (inside your existing venv):
  `pip install -e . pytest`
- Run tests:
  `pytest -q`

These tests validate: (1) STATUS handling, (2) DayBook parsing, (3) empty responses, (4) signed amount calculation.

### After fixing 0-amounts
- Apply migration:
  - If using Docker:  
    `cat warehouse/migrations/0002_add_vchtype.sql | docker exec -i ops-db-1 psql -U inteluser -d intelayer`
- Run tests: `pytest -q`
- Re-run ETL for today: `python agent/run.py`
- In SQL or Metabase, you can now filter by `vchtype` and totals are **signed** (Sales +, Credit Note/Return -).

## Backfill Historical Data

Load historical data or reload after code changes:

```bash
# Quick start - load historical data
python -m agent.backfill 2024-04-01 2024-10-13

# After code changes - clear and reload
python -m agent.clear_and_reload 2024-04-01 2024-10-13

# Always test first with dry run
python -m agent.backfill 2024-04-01 2024-10-13 --dry-run
```

**Documentation:**
- `BACKFILL_QUICKSTART.md` - Quick reference with common commands
- `BACKFILL_GUIDE.md` - Comprehensive guide with workflows and troubleshooting
- `BACKFILL_IMPLEMENTATION_SUMMARY.md` - Technical details and architecture
