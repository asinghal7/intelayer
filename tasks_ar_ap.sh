#!/usr/bin/env bash
set -euo pipefail

# Helper: run DDL and pipelines for AR/AP bill allocations against Docker Postgres
# Usage:
#   ./tasks_ar_ap.sh ddl                    # Run opening bills DDL
#   ./tasks_ar_ap.sh pull-opening-bills     # Load opening bills
#   ./tasks_ar_ap.sh ddl-bills-receivable   # Run bills receivable DDL
#   ./tasks_ar_ap.sh pull-bills-receivable  # Load bills receivable
#   ./tasks_ar_ap.sh ddl-views              # Create billwise outstanding views

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
DDL_OPENING="$ROOT_DIR/warehouse/migrations/0008_mst_opening_bill_allocation.sql"
DDL_RECEIVABLE="$ROOT_DIR/warehouse/migrations/0009_bills_receivable.sql"
DDL_TALLY_LOADER="$ROOT_DIR/warehouse/migrations/0011_tally_loader_trn_tables.sql"
DDL_VIEWS="$ROOT_DIR/warehouse/migrations/0010_view_billwise_outstanding.sql"

case "${1:-}" in
  ddl)
    if [[ ! -f "$DDL_OPENING" ]]; then
      echo "DDL file not found: $DDL_OPENING" >&2
      exit 1
    fi
    # Pipe local SQL into container psql (db service from ops/docker-compose.yml)
    docker compose -f "$ROOT_DIR/ops/docker-compose.yml" exec -T db psql -U inteluser -d intelayer < "$DDL_OPENING"
    ;;

  pull-opening-bills)
    # Ensure DDL first
    "$0" ddl
    # Run the loader using current environment (DB_URL optional; defaults in agent.settings)
    python -m run_ar_ap_opening_bills
    ;;

  ddl-bills-receivable)
    if [[ ! -f "$DDL_RECEIVABLE" ]]; then
      echo "DDL file not found: $DDL_RECEIVABLE" >&2
      exit 1
    fi
    if [[ ! -f "$DDL_TALLY_LOADER" ]]; then
      echo "DDL file not found: $DDL_TALLY_LOADER" >&2
      exit 1
    fi
    # Pipe local SQL into container psql
    docker compose -f "$ROOT_DIR/ops/docker-compose.yml" exec -T db psql -U inteluser -d intelayer < "$DDL_RECEIVABLE"
    docker compose -f "$ROOT_DIR/ops/docker-compose.yml" exec -T db psql -U inteluser -d intelayer < "$DDL_TALLY_LOADER"
    ;;

  pull-bills-receivable)
    # Ensure DDL first
    "$0" ddl-bills-receivable
    # Run the bills receivable pipeline from transactions
    python -m run_bills_receivable
    # Create views after data is loaded
    "$0" ddl-views
    ;;

  ddl-views)
    if [[ ! -f "$DDL_VIEWS" ]]; then
      echo "DDL file not found: $DDL_VIEWS" >&2
      exit 1
    fi
    # Create views for billwise outstanding reports
    docker compose -f "$ROOT_DIR/ops/docker-compose.yml" exec -T db psql -U inteluser -d intelayer < "$DDL_VIEWS"
    ;;

  *)
    echo "Usage: $0 {ddl|pull-opening-bills|ddl-bills-receivable|pull-bills-receivable|ddl-views}" >&2
    exit 2
    ;;
esac


