# Backfill Cheat Sheet

## Three Commands You Need to Know

```bash
# 1. Load historical data
python -m agent.backfill START_DATE END_DATE

# 2. Clear and reload (after code changes)
python -m agent.clear_and_reload START_DATE END_DATE

# 3. Regular daily sync (unchanged)
python -m agent.run
```

## Common Usage

| What You Want | Command |
|---------------|---------|
| Load entire year | `python -m agent.backfill 2024-04-01 2025-03-31` |
| Load last 3 months | `python -m agent.backfill 2024-07-01 2024-10-13` |
| Reload after code fix | `python -m agent.clear_and_reload 2024-04-01 2024-10-13` |
| Test before running | `python -m agent.backfill 2024-04-01 2024-10-13 --dry-run` |
| See per-day progress | `python -m agent.backfill 2024-04-01 2024-10-13 --day-by-day` |

## Date Format

Always use: `YYYY-MM-DD` (e.g., `2024-10-13`)

## Flags

- `--dry-run` = Test without writing to database
- `--day-by-day` = Show progress for each day (slower but detailed)

## Typical Workflow

### First Time Setup
```bash
source .venv/bin/activate
python -m agent.backfill 2024-04-01 2024-10-13
```

### After Making Code Changes
```bash
source .venv/bin/activate
python -m agent.clear_and_reload 2024-04-01 2024-10-13
```

### Daily Automated Sync
```bash
python -m agent.run  # Run via cron/scheduler
```

## Safety

✅ Safe to re-run (uses upsert)  
✅ Won't create duplicates  
✅ Test with `--dry-run` first  
✅ Won't break existing `run.py`  

## Need Help?

- Quick commands: You're reading it!
- Full guide: `BACKFILL_GUIDE.md`
- Examples: `BACKFILL_DEMO.md`
- How it works: `BACKFILL_IMPLEMENTATION_SUMMARY.md`

