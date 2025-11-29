You are improving an existing Python ETL codebase that already fetches data from Tally and loads into Postgres. 
Your task: ADD a minimal, production-ready AR/AP (Receivables/Payables) pipeline that can run TODAY without breaking anything else. 
You MUST read existing files to align with the current architecture, naming, and helpers.

----------------------------------------------------------------
READ & ALIGN (do this first)
----------------------------------------------------------------
1) Open and read these files (if present):
   - instructions.md (project guidance, naming, code style)
   - adapter.py (existing Tally adapter or HTTP client)
   - run.py (current ETL entrypoint)
   - any utils (e.g., db.py, settings.py, logging config, constants, etc.)

2) Determine:
   - Existing DB layer: psycopg vs SQLAlchemy? Use the same one. 
   - Existing env var pattern (.env, pydantic settings, or os.environ)? Reuse it.
   - Existing logger (loguru, stdlib, structlog)? Reuse it.
   - Existing folder structure (e.g., adapters/tally_http/, agent/etl/, sql/ddl/). Mirror it.

3) DO NOT refactor unrelated code. Additive change only.
   - If names already exist, prefer those. 
   - If a helper exists (HTTP POST to Tally, Jinja templating, XML parser helper), reuse it.
   - If a function exists with similar behavior, call it instead of duplicating logic.

----------------------------------------------------------------
SCOPE
----------------------------------------------------------------
Deliver an AR/AP pipeline that:
- Pulls ledger master + outstanding receivables + outstanding payables (bill-wise) from Tally (XML).
- Parses the bill-wise rows robustly (works across common Tally exports).
- Upserts into Postgres with idempotency and safe DDL.
- Produces tables enabling current receivable/payable and historical performance calculations.

----------------------------------------------------------------
FILES TO CREATE (Generate these; merge if they already partially exist)
----------------------------------------------------------------
1) sql/ddl_ar_ap.sql
   - Non-destructive DDL with CREATE TABLE IF NOT EXISTS and safe indexes.
   - Tables:
     a) dim_ledger(ledger_id PK TEXT, ledger_name, ledger_group, gstin, city, pincode, updated_at)
     b) fact_billwise_ref(PK (ledger_id, ref_name), ref_type, voucher_date, due_date, original_amount, pending_amount, last_adjusted_on, last_seen_at)
     c) fact_payment(payment_id PK, ledger_id FK, date, amount, mode, ref_no, created_at)  -- only if you don’t already have it
     d) etl_checkpoints(stream_name PK, last_date)
     e) etl_runs(id, stream_name, started_at, finished_at, status, rows_loaded, error)
   - Two plpgsql helper upsert functions:
     • upsert_dim_ledger(...)
     • upsert_billwise(...)
   - Use NUMERIC(14,2) for amounts, DATE for dates, TIMESTAMPTZ for audit columns.
   - Add appropriate indexes (ledger_id, date; partial index on pending_amount IS NOT NULL).

2) adapters/tally_http/ar_ap/requests/*.xml.j2  (Jinja templates)
   - ledgers.xml.j2 → “List of Accounts” export with <SVCURRENTCOMPANY>.
   - outstanding_receivables.xml.j2 → “Outstanding Receivables” with EXPLODEFLAG=Yes and date window.
   - outstanding_payables.xml.j2 → “Outstanding Payables” with EXPLODEFLAG=Yes and date window.
   - billwise_ledger.xml.j2 → “Ledger Outstandings” for a single ledger (EXPLODEFLAG=Yes; used for future deep-dives).

3) adapters/tally_http/ar_ap/adapter.py
   - Class TallyARAPAdapter(TallyConfig):
     • fetch_ledgers_xml()
     • fetch_outstanding_receivables_xml(from_date, to_date)
     • fetch_outstanding_payables_xml(from_date, to_date)
     • fetch_billwise_for_ledger_xml(ledger_name, from_date, to_date)
   - Reuse existing HTTP client approach if already present (e.g., an existing TallyAdapter). 
     If an adapter exists, create a thin wrapper that calls it; otherwise implement a small POST client (requests) consistent with repo style.
   - Dates formatted as %d-%b-%Y (“01-Apr-2025”).

4) adapters/tally_http/ar_ap/parser.py
   - Use lxml (or existing XML utility) to parse:
     • parse_ledgers(xml_text) → [{ledger_id, ledger_name, ledger_group, gstin, city, pincode}]
     • parse_outstanding_rows(xml_text) → robustly extract bill-wise rows with keys:
         ledger_id (use ledger name as key),
         ref_name, ref_type, voucher_date, due_date,
         original_amount, pending_amount
   - Implement BOTH code paths:
     a) When data appears under <BILLALLOCATIONS.LIST> nodes
     b) Fallback tabular rows under <LINE> (map common column names: LEDGERNAME, BILLREF, BILLTYPE, ORIGINALAMT, PENDINGAMT, BILLDATE, DUEDATE)
   - Defensive parsing: default zeros, strip commas, handle missing tags.

5) agent/etl_ar_ap/loader.py
   - run_ar_ap_pipeline(db_url, tally_url, tally_company, from_dt, to_dt)
     Steps:
      a) Ensure DDL from sql/ddl_ar_ap.sql (use repo’s DB execution style)
      b) Fetch & upsert ledgers
      c) Fetch & upsert Outstanding Receivables
      d) Fetch & upsert Outstanding Payables
      e) Insert an etl_runs row per stream with status and rows_loaded; capture errors
   - Upsert functions call the two SQL functions created in DDL.
   - Respect existing logging pattern.
   - Keep transactions small enough to avoid long-running locks (autocommit or small batches).
   - Idempotent by design; safe to re-run for overlapping date windows.

6) run_ar_ap.py (standalone entrypoint)
   - Reuse repo’s config/env style (do NOT invent a new one).
   - Required env: DB_URL, TALLY_URL, TALLY_COMPANY
   - Optional: FROM_DT, TO_DT (YYYY-MM-DD). If absent, default FY-start..today (FY = Apr-Mar for India).
   - Log start/end and the chosen date window; call run_ar_ap_pipeline().

7) tasks_ar_ap.sh (helper script)
   - Small bash script with targets:
     • ddl: psql "$DB_URL" -f sql/ddl_ar_ap.sql
     • pull: python -m run_ar_ap.py
   - Shebang + set -euo pipefail

----------------------------------------------------------------
INTEGRATION RULES
----------------------------------------------------------------
- If your repo already defines:
  • A Postgres connection factory → use it instead of psycopg.connect.
  • A logger → import and use it.
  • A Tally adapter → wrap/extend it; do not duplicate core HTTP code.
- If paths differ (e.g., src/ instead of root), place files accordingly and fix imports.
- All code must pass mypy/ruff (if the repo uses them). Prefer type hints.
- Keep function names stable and clean; short, action verbs; snake_case.

----------------------------------------------------------------
ACCEPTANCE CRITERIA
----------------------------------------------------------------
1) “Pull” run completes without error against a reachable Tally instance:
   - Ledgers upserted into dim_ledger
   - Receivables & payables bill-wise rows upserted into fact_billwise_ref
   - etl_runs captures status and row counts

2) DDL is re-runnable (idempotent) and never drops or renames existing columns.

3) Parser is robust against common Tally export variants (BILLALLOCATIONS and LINE forms).

4) No changes to existing modules are necessary for the project to run; all new additions are opt-in.

5) Provide clear docstrings and comments where non-obvious mapping is done.

----------------------------------------------------------------
CODE TO GENERATE
----------------------------------------------------------------
Generate the following files with full contents. 
If any similar file already exists, MERGE conservatively: add missing parts, do not delete unrelated code. 
For each file, include a short header comment explaining purpose and integration points.

FILES:
- sql/ddl_ar_ap.sql
- adapters/tally_http/ar_ap/requests/ledgers.xml.j2
- adapters/tally_http/ar_ap/requests/outstanding_receivables.xml.j2
- adapters/tally_http/ar_ap/requests/outstanding_payables.xml.j2
- adapters/tally_http/ar_ap/requests/billwise_ledger.xml.j2
- adapters/tally_http/ar_ap/adapter.py
- adapters/tally_http/ar_ap/parser.py
- agent/etl_ar_ap/loader.py
- run_ar_ap.py
- tasks_ar_ap.sh (chmod +x)

Ensure imports resolve based on the current repo layout after you read adapter.py, run.py, and instructions.md. 
If repository has a different namespace root (e.g., "intelayer"), adjust imports accordingly.

Finally, print a brief RUNBOOK section in the console with:
- Required env vars
- Example commands to run DDL and pull
- Where to find output tables and run logs
