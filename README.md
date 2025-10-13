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
6) Open Metabase: http://localhost:3000 (connect to Postgres).

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

These tests validate: (1) STATUS handling, (2) DayBook parsing, (3) empty responses.
