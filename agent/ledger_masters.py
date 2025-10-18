"""
Ledger Masters ETL

Loads ledger groups and ledgers from Tally Masters XML.
Updates dim_customer with ledger group assignments.

Usage:
    # From Tally HTTP
    python -m agent.ledger_masters --from-tally
    
    # From file (dry-run with preview)
    python -m agent.ledger_masters --from-file sample_ledgers.xml --dry-run --preview 50
    
    # From file (actual load)
    python -m agent.ledger_masters --from-file sample_ledgers.xml
"""

import sys
from pathlib import Path
import psycopg
from loguru import logger
from adapters.tally_http.ledgers_parser import parse_ledger_masters
from adapters.tally_http.client import TallyClient
from agent.settings import DB_URL, TALLY_URL, TALLY_COMPANY


def load_xml_file(file_path: str) -> str:
    """Load XML content from file, auto-detecting encoding."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Try UTF-16 first (common for Tally exports), then UTF-8
    for encoding in ["utf-16", "utf-8"]:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    
    # Fallback: read as binary and try to detect
    raise ValueError(f"Could not decode {file_path} with UTF-16 or UTF-8 encoding")


def fetch_ledgers_from_tally(company: str) -> str:
    """Fetch ledgers XML from Tally via HTTP."""
    from jinja2 import Template
    
    template_file = Path(__file__).parents[1] / "adapters" / "tally_http" / "requests" / "ledgers.xml.j2"
    if not template_file.exists():
        raise FileNotFoundError(f"Template not found: {template_file}")
    
    template = template_file.read_text(encoding="utf-8")
    xml_request = Template(template).render(company=company)
    
    client = TallyClient(TALLY_URL, company)
    logger.info(f"Fetching ledgers from Tally: {company}")
    
    response = client.post_xml(xml_request)
    
    # Check if we got an error response
    if "<LINEERROR>" in response:
        logger.warning(f"Tally returned error: {response}")
        raise ValueError(f"Tally error: {response}")
    
    # Check if we got meaningful data
    if "<LEDGER" in response or "<GROUP" in response:
        logger.success(f"Successfully fetched ledger data")
    else:
        logger.warning(f"No LEDGER or GROUP elements found in response")
    
    return response


def ensure_schema(conn):
    """Ensure required tables exist."""
    migration_file = Path(__file__).parents[1] / "warehouse" / "migrations" / "0007_ledger_masters.sql"
    if migration_file.exists():
        sql = migration_file.read_text(encoding="utf-8")
        with conn.cursor() as cur:
            cur.execute(sql)
        logger.info("Schema validated/created")
    else:
        logger.warning(f"Migration file not found: {migration_file}")


def upsert_ledger_groups(conn, groups: list[dict]) -> tuple[int, int]:
    """
    Upsert ledger groups into dim_ledger_group.
    Returns (inserted, updated) counts.
    """
    if not groups:
        return (0, 0)
    
    inserted = 0
    updated = 0
    
    with conn.cursor() as cur:
        for group in groups:
            # Check if exists (by GUID if available, else by name)
            if group["guid"]:
                cur.execute("SELECT guid FROM dim_ledger_group WHERE guid = %s", (group["guid"],))
                exists = cur.fetchone() is not None
            else:
                cur.execute("SELECT name FROM dim_ledger_group WHERE name = %s", (group["name"],))
                exists = cur.fetchone() is not None
            
            # Upsert by GUID if available
            if group["guid"]:
                cur.execute("""
                    INSERT INTO dim_ledger_group (guid, name, parent_name, alter_id, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (guid) DO UPDATE SET
                        name = EXCLUDED.name,
                        parent_name = EXCLUDED.parent_name,
                        alter_id = EXCLUDED.alter_id,
                        updated_at = NOW()
                """, (group["guid"], group["name"], group["parent_name"], group["alter_id"]))
            else:
                # Fallback: upsert by name
                cur.execute("""
                    INSERT INTO dim_ledger_group (name, parent_name, alter_id, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (name) DO UPDATE SET
                        parent_name = EXCLUDED.parent_name,
                        alter_id = EXCLUDED.alter_id,
                        updated_at = NOW()
                """, (group["name"], group["parent_name"], group["alter_id"]))
            
            if exists:
                updated += 1
            else:
                inserted += 1
    
    return (inserted, updated)


def update_customer_ledger_groups(conn, ledgers: list[dict]) -> int:
    """
    Update dim_customer.ledger_group_name based on ledger parent assignments.
    
    Args:
        conn: Database connection
        ledgers: List of ledger dicts with name and parent_name
        
    Returns:
        Number of customers updated
    """
    if not ledgers:
        return 0
    
    with conn.cursor() as cur:
        # Create temp table with ledger → group mapping
        cur.execute("""
            CREATE TEMP TABLE IF NOT EXISTS ledger_to_group (
                ledger_name text,
                group_name text
            )
        """)
        
        # Clear and populate temp table
        cur.execute("TRUNCATE TABLE ledger_to_group")
        
        for ledger in ledgers:
            if ledger.get("parent_name"):
                cur.execute("""
                    INSERT INTO ledger_to_group (ledger_name, group_name)
                    VALUES (%s, %s)
                """, (ledger["name"], ledger["parent_name"]))
        
        # Update dim_customer with ledger group
        cur.execute("""
            UPDATE dim_customer c
            SET ledger_group_name = ltg.group_name
            FROM ledger_to_group ltg
            WHERE (c.customer_id = ltg.ledger_name OR c.name = ltg.ledger_name)
              AND (c.ledger_group_name IS NULL OR c.ledger_group_name != ltg.group_name)
        """)
        
        updated_count = cur.rowcount
        
        # Clean up temp table
        cur.execute("DROP TABLE IF EXISTS ledger_to_group")
        
        return updated_count


def preview_data(conn, limit: int = 50) -> dict:
    """
    Query database to show preview of loaded data.
    Returns dict with counts and sample rows.
    """
    with conn.cursor() as cur:
        # Get counts
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM dim_ledger_group) AS groups,
                (SELECT COUNT(*) FROM dim_customer WHERE ledger_group_name IS NOT NULL) AS customers_with_group
        """)
        counts = cur.fetchone()
        
        # Get sample groups (roots and children)
        cur.execute("""
            SELECT g.name AS root, c.name AS child
            FROM dim_ledger_group g
            LEFT JOIN dim_ledger_group c ON c.parent_name = g.name
            WHERE g.parent_name IS NULL
            ORDER BY g.name, c.name
            LIMIT %s
        """, (limit,))
        group_tree = cur.fetchall()
        
        # Get sample customers with their ledger groups
        cur.execute("""
            SELECT name, ledger_group_name
            FROM dim_customer
            WHERE ledger_group_name IS NOT NULL
            ORDER BY ledger_group_name, name
            LIMIT %s
        """, (limit,))
        customers_sample = cur.fetchall()
    
    return {
        "counts": {
            "groups": counts[0] if counts else 0,
            "customers_with_group": counts[1] if counts else 0,
        },
        "group_tree": group_tree,
        "customers_sample": customers_sample,
    }


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    # Parse arguments
    from_file = None
    from_tally = False
    dry_run = False
    preview_limit = 50
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--from-file" and i + 1 < len(sys.argv):
            from_file = sys.argv[i + 1]
            i += 2
        elif arg == "--from-tally":
            from_tally = True
            i += 1
        elif arg == "--dry-run":
            dry_run = True
            i += 1
        elif arg == "--preview" and i + 1 < len(sys.argv):
            preview_limit = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    # Validate inputs
    if not from_file and not from_tally:
        logger.error("Must specify either --from-file or --from-tally")
        sys.exit(1)
    
    # Load XML
    if from_file:
        logger.info(f"Loading XML from file: {from_file}")
        xml_text = load_xml_file(from_file)
    elif from_tally:
        logger.info(f"Fetching ledgers from Tally: {TALLY_COMPANY}")
        xml_text = fetch_ledgers_from_tally(TALLY_COMPANY)
        # Debug: save the raw response
        try:
            debug_path = Path("tally_ledgers_response.xml")
            debug_path.write_text(xml_text, encoding="utf-8")
            logger.info(f"Saved Tally response to {debug_path} (size={len(xml_text)} chars)")
        except Exception as _e:
            logger.debug(f"Could not write debug XML: {_e}")
    
    # Parse
    logger.info("Parsing ledgers XML...")
    data = parse_ledger_masters(xml_text)
    
    logger.info(f"Parsed: {len(data['groups'])} groups, {len(data['ledgers'])} ledgers")
    
    # Show what would be loaded
    if data['groups']:
        root_groups = [g for g in data['groups'] if not g['parent_name']]
        logger.info(f"Found {len(root_groups)} root groups:")
        for g in root_groups[:10]:  # Show first 10
            logger.info(f"  - {g['name']}")
        if len(root_groups) > 10:
            logger.info(f"  ... and {len(root_groups) - 10} more")
    
    if dry_run:
        logger.warning("DRY RUN MODE - No data will be written to database")
        logger.info("\n=== Preview (dry-run) ===")
        logger.info(f"Would upsert {len(data['groups'])} ledger groups")
        logger.info(f"Would update {len(data['ledgers'])} customer ledger group assignments")
        
        if data['ledgers']:
            logger.info("\nSample ledger → group mappings (first 10):")
            for ledger in data['ledgers'][:10]:
                if ledger.get('parent_name'):
                    logger.info(f"  {ledger['name']} → {ledger['parent_name']}")
        
        return
    
    # Connect to DB and load data
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        logger.info("Ensuring schema exists...")
        ensure_schema(conn)
        
        logger.info("Upserting ledger groups...")
        groups_ins, groups_upd = upsert_ledger_groups(conn, data['groups'])
        logger.success(f"Groups: {groups_ins} inserted, {groups_upd} updated")
        
        logger.info("Updating customer ledger group assignments...")
        customers_updated = update_customer_ledger_groups(conn, data['ledgers'])
        logger.success(f"Customers updated: {customers_updated}")
        
        # Preview
        logger.info("\n=== Preview ===")
        preview = preview_data(conn, preview_limit)
        
        logger.info(f"\nTotals:")
        logger.info(f"  Ledger Groups: {preview['counts']['groups']}")
        logger.info(f"  Customers with Ledger Group: {preview['counts']['customers_with_group']}")
        
        if preview['group_tree']:
            logger.info(f"\nLedger Group Hierarchy (first {min(len(preview['group_tree']), preview_limit)}):")
            current_root = None
            for row in preview['group_tree'][:20]:
                root, child = row
                if root != current_root:
                    logger.info(f"  [{root}]")
                    current_root = root
                if child:
                    logger.info(f"    - {child}")
        
        if preview['customers_sample']:
            logger.info(f"\nSample Customers with Ledger Groups (first {min(len(preview['customers_sample']), preview_limit)}):")
            current_group = None
            for row in preview['customers_sample'][:20]:
                name, group = row
                if group != current_group:
                    logger.info(f"  [{group}]")
                    current_group = group
                logger.info(f"    - {name}")
        
        # Final checklist
        logger.info("\n=== Developer Checklist ===")
        logger.success(f"✓ Ledger groups loaded: {preview['counts']['groups']}")
        logger.success(f"✓ Customers with ledger group: {preview['counts']['customers_with_group']}")
        
        # Check for customers without ledger group
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM dim_customer
                WHERE ledger_group_name IS NULL
            """)
            without_group = cur.fetchone()[0]
            if without_group > 0:
                logger.warning(f"⚠ {without_group} customers have no ledger group assigned")


if __name__ == "__main__":
    main()

