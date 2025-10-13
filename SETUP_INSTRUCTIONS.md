# Setup Instructions

## Post-Creation Steps

### 1. Create Environment File
Since `.env` files are gitignored by default, create it manually:

```bash
cat > .env << 'EOF'
# Tally HTTP server (Windows VM)
TALLY_URL=http://192.168.1.50:9000
TALLY_COMPANY=Ashirwad Electronics (23-24/24-25)

# Postgres (Docker Compose)
DB_URL=postgresql://inteluser:change_me@localhost:5432/intelayer
EOF
```

**Update the values** with your actual Tally server IP and company name.

### 2. Start Infrastructure (Postgres + Metabase)

```bash
docker compose -f ops/docker-compose.yml up -d
```

This will start:
- PostgreSQL on port 5432
- Metabase on port 3000

### 3. Apply Database Schema

```bash
psql $DB_URL -f warehouse/ddl/0001_cdm.sql
```

Or if psql isn't in PATH:
```bash
docker exec -i $(docker ps -qf "name=db") psql -U inteluser -d intelayer < warehouse/ddl/0001_cdm.sql
```

### 4. Install Python Dependencies

Activate your existing venv and install the project:

```bash
source venv/bin/activate
pip install -e .
```

This installs the project in editable mode with all dependencies from `pyproject.toml`.

### 5. Run ETL Once

```bash
python agent/run.py
```

This will:
- Connect to Tally and fetch daybook data
- Parse and transform the data
- Load it into Postgres fact tables
- Log the ETL run

### 6. Open Metabase

Navigate to http://localhost:3000

**First-time setup:**
1. Create admin account
2. Connect to Postgres:
   - Database type: PostgreSQL
   - Host: db (or localhost if accessing from host machine)
   - Port: 5432
   - Database name: intelayer
   - Username: inteluser
   - Password: change_me

3. Start building dashboards!

## Verification

### Check if data loaded:

```bash
psql $DB_URL -c "SELECT count(*) FROM fact_invoice;"
psql $DB_URL -c "SELECT * FROM etl_logs ORDER BY run_at DESC LIMIT 5;"
```

### Run health check:

```bash
python ops/health_check.py
```

Should output: `ETL healthy`

## Scheduling ETL

### Option 1: Cron (Linux/Mac)

```bash
crontab -e
```

Add:
```
# Run ETL every hour
0 * * * * cd /path/to/intelayer && source venv/bin/activate && python agent/run.py >> logs/etl.log 2>&1
```

### Option 2: systemd timer (Linux)

Create `/etc/systemd/system/intelayer-etl.service`:
```ini
[Unit]
Description=Intelayer ETL

[Service]
Type=oneshot
User=youruser
WorkingDirectory=/path/to/intelayer
Environment="PATH=/path/to/intelayer/venv/bin"
ExecStart=/path/to/intelayer/venv/bin/python agent/run.py
```

Create `/etc/systemd/system/intelayer-etl.timer`:
```ini
[Unit]
Description=Run Intelayer ETL hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl enable --now intelayer-etl.timer
```

### Option 3: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily, repeat every 1 hour
4. Action: Start a program
   - Program: `C:\path\to\intelayer\venv\Scripts\python.exe`
   - Arguments: `agent/run.py`
   - Start in: `C:\path\to\intelayer`

## Backup

### Manual backup:

```bash
export DB_URL=postgresql://inteluser:change_me@localhost:5432/intelayer
./ops/backup.sh
```

Backups are stored in `ops/backups/` and automatically cleaned after 14 days.

### Schedule backups:

Add to crontab:
```
# Daily backup at 2 AM
0 2 * * * cd /path/to/intelayer && DB_URL=postgresql://... ./ops/backup.sh >> logs/backup.log 2>&1
```

## Troubleshooting

### Tally Connection Issues

```bash
# Test Tally connectivity
curl -v http://192.168.1.50:9000
```

If this fails:
1. Ensure Tally is running
2. Enable ODBC Server in Tally: Gateway → F1 Help → Settings → Connectivity → ODBC Server
3. Check Windows Firewall allows port 9000
4. Verify you're on the same network

### Database Connection Issues

```bash
# Test database connection
psql $DB_URL -c "SELECT version();"
```

If this fails:
1. Check Docker containers are running: `docker ps`
2. Check Docker logs: `docker logs $(docker ps -qf "name=db")`
3. Verify DB_URL in .env

### ETL Errors

Check logs:
```bash
psql $DB_URL -c "SELECT * FROM etl_logs WHERE status='error' ORDER BY run_at DESC LIMIT 10;"
```

Run with debugging:
```bash
python -m pdb agent/run.py
```

## Next Steps

1. **Verify reconciliation:** Compare monthly totals in Postgres vs Tally DayBook
2. **Build dashboards:** Create sales, inventory, and customer analytics in Metabase
3. **Add more adapters:** Extend for other ERP systems
4. **Implement AR tracking:** Add accounts receivable facts and ageing analysis
5. **Set up alerts:** Use Metabase alerts or custom monitoring

