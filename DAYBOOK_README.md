# Tally Daybook Voucher Counter

A Python script to fetch daybook reports from Tally ERP via XML API and count vouchers for a specified date.

## Features

- ✅ Fetches daybook data directly from Tally via XML API
- ✅ Date filtering applied server-side for efficiency
- ✅ Configurable via command-line arguments or config file
- ✅ Comprehensive error handling
- ✅ XML sanitization to handle invalid characters from Tally
- ✅ Verbose mode to view detailed voucher information
- ✅ Debug mode to save raw XML responses

## Prerequisites

1. **Tally ERP** must be running with ODBC Server enabled:
   - Open Tally
   - Go to: `Gateway of Tally → F1 (Help) → Settings → Connectivity → ODBC Server`
   - Enable ODBC Server
   - Note the port (default: 9000)

2. **Python 3.7+** installed on your system

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd /Users/akshatsinghal/Desktop/Akshat/Work/ERP/intelayer
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the script:**
   ```bash
   cp config.ini.example config.ini
   # Edit config.ini with your Tally server details
   ```

## Configuration

### Option 1: Using config.ini (Recommended)

Edit `config.ini`:

```ini
[tally]
url = http://192.168.0.189:9000
company = Ashirwad Electronics (23-24/24-25)
```

### Option 2: Command-Line Arguments

Pass arguments directly when running the script (overrides config.ini).

## Usage

### Basic Usage

```bash
# Fetch today's daybook (uses config.ini)
python fetch_daybook.py

# Fetch for a specific date
python fetch_daybook.py --date 20251011

# Use command-line arguments instead of config file
python fetch_daybook.py --tally-url http://192.168.0.189:9000 --company "Your Company Name"
```

### Advanced Usage

```bash
# Verbose mode - show detailed voucher information
python fetch_daybook.py --verbose

# Debug mode - save raw XML response for troubleshooting
python fetch_daybook.py --debug

# Specific date with custom timeout
python fetch_daybook.py --date 20251001 --timeout 60

# Combine options
python fetch_daybook.py --date 20251011 --verbose --debug
```

### Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--tally-url` | Tally server URL | From config.ini |
| `--company` | Company name (exact match) | From config.ini |
| `--date` | Date in YYYYMMDD format | Today |
| `--config` | Path to config file | config.ini |
| `--verbose`, `-v` | Show detailed voucher info | False |
| `--debug` | Save raw XML to debug.xml | False |
| `--timeout` | Request timeout in seconds | 30 |

## Output

### Normal Mode
```
Fetching daybook from Tally...
  Server: http://192.168.0.189:9000
  Company: Ashirwad Electronics (23-24/24-25)
  Date: 11-10-2025

✓ Successfully fetched daybook report
  Total Vouchers: 45
```

### Verbose Mode
```
Fetching daybook from Tally...
  Server: http://192.168.0.189:9000
  Company: Ashirwad Electronics (23-24/24-25)
  Date: 11-10-2025

✓ Successfully fetched daybook report
  Total Vouchers: 45

Voucher Details:
--------------------------------------------------------------------------------
  1. Type: Receipt              | Number: 1               | Party: Customer A
  2. Type: Payment              | Number: 2               | Party: Supplier B
  3. Type: Sales                | Number: 3               | Party: Customer C
...
--------------------------------------------------------------------------------
```

## Troubleshooting

### Connection Errors

**Error:** `Failed to connect to Tally server`

**Solutions:**
1. Verify Tally is running
2. Check ODBC Server is enabled in Tally settings
3. Confirm the IP address and port (default: 9000)
4. Test connectivity: `curl http://192.168.0.189:9000`
5. Ensure you're on the same network as the Tally server

### XML Parse Errors

**Error:** `Failed to parse XML response`

**Solutions:**
1. Run with `--debug` flag to save the raw XML response:
   ```bash
   python fetch_daybook.py --debug
   ```
2. Check the generated files:
   - `debug.xml` - Raw response from Tally
   - `error_response.xml` - Response that failed to parse
   - `error_response_sanitized.xml` - After sanitization
3. Common causes:
   - Invalid characters in voucher data (narrations, names)
   - Special characters in company name
   - XML formatting issues from Tally

### Company Not Found

**Error:** `Error: Company name is required`

**Solutions:**
1. Verify company name exactly matches Tally (case-sensitive)
2. Include all special characters, spaces, and year suffixes
3. Check company name in Tally: `Alt+F3` in Tally to see company list

### Date Format Errors

**Error:** `Invalid date format`

**Solution:**
- Use YYYYMMDD format: `20251011` for October 11, 2025
- Example: `--date 20251011`

## Technical Details

### XML Request Format

The script sends POST requests to Tally with this XML structure:

```xml
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Day Book</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVCURRENTCOMPANY>Company Name</SVCURRENTCOMPANY>
        <SVFROMDATE TYPE="Date">YYYYMMDD</SVFROMDATE>
        <SVTODATE TYPE="Date">YYYYMMDD</SVTODATE>
        <EXPLODEFLAG>Yes</EXPLODEFLAG>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>
```

### XML Sanitization

The script automatically removes:
- Invalid XML character entity references (&#x0; through &#x1F;)
- Raw control characters that aren't valid in XML
- This handles common issues with Tally's XML output

### Error Handling

The script handles:
- Network connectivity issues
- HTTP errors (timeouts, server errors)
- XML parsing errors with automatic file saving for debugging
- Missing configuration
- Invalid date formats
- Tally API errors

## Integration with ERP Pipeline

This script is part of the Intelayer ERP system and can be integrated into:

1. **ETL Pipelines:** Extract daybook data for warehousing
2. **Monitoring:** Track daily voucher counts
3. **Reporting:** Generate daily transaction summaries
4. **Automation:** Schedule with cron for automatic fetching

### Example: Daily Cron Job

```bash
# Add to crontab (crontab -e)
0 18 * * * cd /path/to/intelayer && source venv/bin/activate && python fetch_daybook.py >> logs/daybook.log 2>&1
```

This runs daily at 6 PM and logs output.

## Development

### Running Tests

```bash
# Test with today's date
python fetch_daybook.py --verbose

# Test with a specific historical date
python fetch_daybook.py --date 20241001 --verbose

# Test connection only (debug mode)
python fetch_daybook.py --debug
```

### Extending the Script

To add more data extraction:

1. Modify `parse_voucher_count()` method in `fetch_daybook.py`
2. Add XML parsing for additional fields (amounts, ledgers, etc.)
3. Update the `voucher_details` dictionary structure

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Run with `--debug` flag to capture XML responses
3. Verify Tally ODBC server settings
4. Check Tally API documentation: [https://help.tallysolutions.com](https://help.tallysolutions.com)

## License

Part of the Intelayer ERP system.

## Version

1.0.0 - Initial release with daybook fetching and voucher counting

