# Backfill Guide

This guide explains how to backfill historical daybook data into the warehouse.

## Overview

The backfill script (`agent/backfill.py`) allows you to load historical data from Tally into your warehouse. It uses the same infrastructure as the regular daily ETL (`agent/run.py`), so any code updates you make will automatically apply to both.

## Usage

### Basic Backfill (Recommended)

Backfill entire date range at once - **fastest option**:

```bash
source .venv/bin/activate
python -m agent.backfill 2024-04-01 2024-10-13
```

### Day-by-Day Backfill

Backfill one day at a time - useful for debugging or when you need granular logs:

```bash
python -m agent.backfill 2024-04-01 2024-10-13 --day-by-day
```

### Dry Run

Test what would be fetched without writing to database:

```bash
python -m agent.backfill 2024-04-01 2024-10-13 --dry-run
```

### Clear and Reload (Helper Script)

Delete existing data and reload fresh data in one command:

```bash
# Clear and reload
python -m agent.clear_and_reload 2024-04-01 2024-10-13

# Test first with dry run
python -m agent.clear_and_reload 2024-04-01 2024-10-13 --dry-run

# Day-by-day mode
python -m agent.clear_and_reload 2024-04-01 2024-10-13 --day-by-day
```

## Common Workflows

### 1. Initial Historical Data Load

```bash
# Load entire financial year
python -m agent.backfill 2024-04-01 2025-10-13
```

### 2. Clearing and Reloading Data

**Easy Way** - Use the helper script (recommended):

```bash
# Clear and reload in one command
python -m agent.clear_and_reload 2024-04-01 2024-10-13

# Test with dry run first
python -m agent.clear_and_reload 2024-04-01 2024-10-13 --dry-run

# Use day-by-day mode for granular progress
python -m agent.clear_and_reload 2024-04-01 2024-10-13 --day-by-day
```

**Manual Way** - If you prefer to do it step by step:

```bash
# 1. Clear the data (in psql or your DB tool)
psql $DB_URL -c "DELETE FROM fact_invoice WHERE date >= '2024-04-01';"

# 2. Reset checkpoint (optional - only if you want run.py to re-sync)
psql $DB_URL -c "UPDATE etl_checkpoints SET last_date = '2024-03-31' WHERE stream_name = 'invoices';"

# 3. Backfill the data
python -m agent.backfill 2024-04-01 2024-10-13
```

### 3. Filling a Specific Date Range Gap

```bash
# If you notice missing data for a specific period
python -m agent.backfill 2024-08-15 2024-08-20
```

## How It Works

1. **Shared Logic**: Both `run.py` and `backfill.py` use the same:
   - Tally adapter (`adapters/tally_http/adapter.py`)
   - XML template (`adapters/tally_http/requests/daybook.xml.j2`)
   - Upsert logic (`agent/run.py::upsert_invoice`)
   
2. **Date Filtering**: Tally's DayBook export returns ALL vouchers regardless of the date parameters in the XML request. The adapter filters the results on our side to only include vouchers within the requested date range. This is handled automatically.

3. **Upsert Safety**: The `upsert_invoice` function uses `ON CONFLICT DO UPDATE`, so you can safely re-run backfills without creating duplicates.

## Key Differences: Scripts Comparison

| Feature | `run.py` | `backfill.py` | `clear_and_reload.py` |
|---------|----------|---------------|----------------------|
| Purpose | Daily incremental sync | Historical data load | Clear + reload data |
| Date Range | Auto (checkpoint to today) | Manual (you specify) | Manual (you specify) |
| Checkpoint | Updates checkpoint | No checkpoint updates | No checkpoint updates |
| ETL Logs | Writes to `etl_logs` table | No logs (manual operation) | No logs (manual operation) |
| Overlap | 1 day overlap for late edits | No overlap (exact range) | No overlap (exact range) |
| Deletes Data | No | No | Yes (step 1) |
| Scheduling | Run via cron/scheduler | Run manually as needed | Run manually as needed |

## Tips

1. **Start with Dry Run**: Always test with `--dry-run` first to verify dates
2. **Use Range Mode**: Default range mode is faster for large date ranges
3. **Day-by-Day for Debugging**: Use `--day-by-day` if you need to see progress per day or troubleshoot specific dates
4. **Monitor Progress**: The script logs progress every 100 invoices in range mode
5. **Safe to Re-run**: Thanks to upsert logic, you can safely re-run backfills

## Troubleshooting

### Error: "Connection refused"
- Check that Tally is running and accessible at the URL in your `.env` file
- Verify `TALLY_URL` setting

### Error: "Company not found"
- Verify `TALLY_COMPANY` matches exactly (case-sensitive)

### No data returned
- Check that the date range has data in Tally
- Use `--day-by-day` to see which specific days have data

### Database errors
- Verify `DB_URL` connection string in `.env`
- Check that tables exist (run migrations if needed)

### Performance note
- Tally returns ALL vouchers regardless of date range (this is Tally's DayBook export behavior)
- The adapter filters results on our side to match the requested date range
- This means requests take the same time regardless of date range
- For large datasets, consider using the default range mode instead of day-by-day

## Examples

```bash
# Financial year 2024-25
python -m agent.backfill 2024-04-01 2025-03-31

# Last quarter
python -m agent.backfill 2024-07-01 2024-09-30

# Specific month with day-by-day logging
python -m agent.backfill 2024-08-01 2024-08-31 --day-by-day

# Test before running
python -m agent.backfill 2024-04-01 2024-04-05 --dry-run
```

## Integration with Regular ETL

After backfilling historical data, your regular `run.py` will continue from its checkpoint:

```bash
# Backfill historical
python -m agent.backfill 2024-04-01 2024-10-12

# Regular daily ETL continues as normal (doesn't interfere)
python -m agent.run
```

The checkpoint mechanism ensures `run.py` tracks its own progress independently of backfill operations.

