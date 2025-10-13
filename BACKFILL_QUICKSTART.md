# Backfill Quick Reference

## TL;DR - Most Common Commands

```bash
# Activate virtual environment first
source .venv/bin/activate

# Initial load of historical data
python -m agent.backfill 2024-04-01 2024-10-13

# After code changes - clear and reload
python -m agent.clear_and_reload 2024-04-01 2024-10-13

# Test before running
python -m agent.backfill 2024-04-01 2024-10-13 --dry-run

# Regular daily ETL (unchanged)
python -m agent.run
```

## Three Scripts

| Script | When to Use | Command |
|--------|-------------|---------|
| `backfill.py` | Load historical data | `python -m agent.backfill START END` |
| `clear_and_reload.py` | Reload after code changes | `python -m agent.clear_and_reload START END` |
| `run.py` | Daily automated sync | `python -m agent.run` |

## Flags

- `--dry-run` - Test without writing to database
- `--day-by-day` - Show progress per day (slower but more detailed logs)

## Examples

```bash
# Load entire financial year
python -m agent.backfill 2024-04-01 2025-03-31

# Clear and reload last 3 months
python -m agent.clear_and_reload 2024-07-01 2024-10-13

# Fill a gap in data
python -m agent.backfill 2024-08-15 2024-08-20

# Debug with detailed logs
python -m agent.backfill 2024-09-01 2024-09-05 --day-by-day

# Always test first!
python -m agent.clear_and_reload 2024-04-01 2024-10-13 --dry-run
```

## Typical Workflow After Code Changes

```bash
# 1. Activate venv
source .venv/bin/activate

# 2. Test the change with a small range
python -m agent.clear_and_reload 2024-10-10 2024-10-10

# 3. If looks good, reload full range
python -m agent.clear_and_reload 2024-04-01 2024-10-13
```

## Need More Details?

See `BACKFILL_GUIDE.md` for comprehensive documentation.

