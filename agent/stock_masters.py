"""
Stock Masters ETL - Phase 1

Loads stock groups (brands), units (UOM), and stock items (SKUs) from Tally Masters XML.
Supports both file-based and HTTP export modes.

Usage:
    # From file (dry-run with preview)
    python -m agent.stock_masters --from-file samplemaster.xml --dry-run --preview 50
    
    # From file (actual load)
    python -m agent.stock_masters --from-file samplemaster.xml
    
    # From Tally HTTP (future - requires HTTP export template)
    python -m agent.stock_masters --from-tally --preview 100
    
    # Filter to specific brands (root stock groups)
    python -m agent.stock_masters --from-file samplemaster.xml --brands "Whirlpool,Voltas,V-Guard Industries Ltd" --dry-run

    # Export to CSV
    python -m agent.stock_masters --from-file samplemaster.xml --export-csv masters.csv
"""

import sys
import csv
from pathlib import Path
import psycopg
from loguru import logger
from adapters.tally_http.masters_parser import parse_masters
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


def fetch_masters_from_tally(company: str) -> str:
    """Fetch masters XML from Tally via HTTP, trying different report names."""
    from jinja2 import Template
    
    # Fetch multiple datasets: All Masters (groups), Units, and Stock Items
    report_templates = [
        "masters.xml.j2",               # All Masters (groups)
        "units_data.xml.j2",            # List of Accounts - Units
        "stock_items_data.xml.j2",      # List of Accounts - Stock Items
    ]
    
    client = TallyClient(TALLY_URL, company)
    all_responses: list[str] = []
    
    for template_name in report_templates:
        try:
            template_file = Path(__file__).parents[1] / "adapters" / "tally_http" / "requests" / template_name
            if not template_file.exists():
                logger.warning(f"Template {template_name} not found, skipping")
                continue
                
            template = template_file.read_text(encoding="utf-8")
            xml_request = Template(template).render(company=company)
            
            logger.info(f"Trying report template: {template_name}")
            response = client.post_xml(xml_request)
            
            # Check if we got an error response
            if "<LINEERROR>" in response and "Could not find Report" in response:
                logger.warning(f"Template {template_name} failed: {response}")
                continue
            
            # Check if we got meaningful data
            if "<STOCKGROUP" in response or "<UNIT" in response or "<STOCKITEM" in response or "<COLLECTION" in response:
                logger.success(f"Success with template: {template_name}")
                all_responses.append(response)
            else:
                logger.warning(f"Template {template_name} returned no stock data")
                
        except Exception as e:
            logger.warning(f"Template {template_name} failed: {e}")
            continue
    
    if not all_responses:
        logger.error("No data fetched from any template")
        return "<ENVELOPE><BODY><DATA></DATA></BODY></ENVELOPE>"
    
    # Combine responses by concatenating the contents inside <ENVELOPE> (best-effort)
    combined = "<ENVELOPE><BODY><DATA>" + "".join(all_responses) + "</DATA></BODY></ENVELOPE>"
    return combined


def ensure_schema(conn):
    """Ensure required tables exist."""
    migration_file = Path(__file__).parents[1] / "warehouse" / "migrations" / "0004_stock_masters.sql"
    if migration_file.exists():
        sql = migration_file.read_text(encoding="utf-8")
        with conn.cursor() as cur:
            cur.execute(sql)
        logger.info("Schema validated/created")
    else:
        logger.warning(f"Migration file not found: {migration_file}")


def upsert_units(conn, units: list[dict]) -> tuple[int, int]:
    """
    Upsert units into dim_uom.
    Returns (inserted, updated) counts.
    """
    if not units:
        return (0, 0)
    
    inserted = 0
    updated = 0
    
    with conn.cursor() as cur:
        for unit in units:
            # Check if exists
            cur.execute("SELECT uom_name FROM dim_uom WHERE uom_name = %s", (unit["name"],))
            exists = cur.fetchone() is not None
            
            cur.execute("""
                INSERT INTO dim_uom (uom_name, original_name, gst_rep_uom, is_simple, alter_id, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (uom_name) DO UPDATE SET
                    original_name = EXCLUDED.original_name,
                    gst_rep_uom = EXCLUDED.gst_rep_uom,
                    is_simple = EXCLUDED.is_simple,
                    alter_id = EXCLUDED.alter_id,
                    updated_at = NOW()
            """, (
                unit["name"],
                unit["original_name"],
                unit["gst_rep_uom"],
                unit["is_simple"],
                unit["alter_id"],
            ))
            
            if exists:
                updated += 1
            else:
                inserted += 1
    
    return (inserted, updated)


def upsert_groups(conn, groups: list[dict]) -> tuple[int, int]:
    """
    Upsert stock groups into dim_stock_group.
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
                cur.execute("SELECT guid FROM dim_stock_group WHERE guid = %s", (group["guid"],))
                exists = cur.fetchone() is not None
            else:
                cur.execute("SELECT name FROM dim_stock_group WHERE name = %s", (group["name"],))
                exists = cur.fetchone() is not None
            
            # Upsert by GUID if available
            if group["guid"]:
                cur.execute("""
                    INSERT INTO dim_stock_group (guid, name, parent_name, alter_id, updated_at)
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
                    INSERT INTO dim_stock_group (name, parent_name, alter_id, updated_at)
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


def upsert_items(conn, items: list[dict]) -> tuple[int, int]:
    """
    Upsert stock items into dim_item.
    Returns (inserted, updated) counts.
    """
    if not items:
        return (0, 0)
    
    inserted = 0
    updated = 0
    
    with conn.cursor() as cur:
        for item in items:
            # item_id = guid if available, else name
            item_id = item["guid"] if item["guid"] else item["name"]
            
            # Check if exists
            cur.execute("SELECT item_id FROM dim_item WHERE item_id = %s", (item_id,))
            exists = cur.fetchone() is not None
            
            # Upsert with smart merging (keep non-null existing values)
            cur.execute("""
                INSERT INTO dim_item (item_id, guid, name, parent_name, uom, hsn, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (item_id) DO UPDATE SET
                    guid = COALESCE(EXCLUDED.guid, dim_item.guid),
                    name = COALESCE(EXCLUDED.name, dim_item.name),
                    parent_name = COALESCE(EXCLUDED.parent_name, dim_item.parent_name),
                    uom = COALESCE(NULLIF(EXCLUDED.uom, ''), dim_item.uom),
                    hsn = COALESCE(NULLIF(EXCLUDED.hsn, ''), dim_item.hsn),
                    updated_at = NOW()
            """, (
                item_id,
                item["guid"],
                item["name"],
                item["parent_name"],
                item["base_units"],
                item["hsn"],
            ))
            
            if exists:
                updated += 1
            else:
                inserted += 1
    
    return (inserted, updated)


def compute_brands(conn):
    """
    Compute brand_name for all items in dim_item by walking up the stock_group hierarchy
    to find the root group (group with NULL parent_name).
    """
    with conn.cursor() as cur:
        # Use recursive CTE to find root group for each item
        cur.execute("""
            WITH RECURSIVE grp AS (
                -- Start: get each item's immediate parent group
                SELECT i.item_id, g.name AS group_name, g.parent_name, 1 AS depth
                FROM dim_item i
                LEFT JOIN dim_stock_group g ON g.name = i.parent_name
                
                UNION ALL
                
                -- Recurse: walk up the hierarchy
                SELECT grp.item_id, g2.name, g2.parent_name, grp.depth + 1
                FROM grp
                JOIN dim_stock_group g2 ON g2.name = grp.parent_name
                WHERE grp.depth < 10  -- safety limit
            ),
            root AS (
                -- Find the root group (one with NULL parent_name)
                SELECT 
                    item_id,
                    (ARRAY_AGG(group_name ORDER BY 
                        CASE WHEN parent_name IS NULL THEN 0 ELSE 1 END, 
                        depth ASC
                    ))[1] AS root_group
                FROM grp
                GROUP BY item_id
            )
            UPDATE dim_item i
            SET brand = COALESCE(r.root_group, i.parent_name)
            FROM root r
            WHERE r.item_id = i.item_id
              AND COALESCE(i.brand, '') <> COALESCE(r.root_group, i.parent_name, '')
        """)
        
        updated = cur.rowcount
        logger.info(f"Updated brand for {updated} items")
        return updated


def preview_data(conn, limit: int = 50) -> dict:
    """
    Query database to show preview of loaded data.
    Returns dict with counts and sample rows.
    """
    with conn.cursor() as cur:
        # Get counts
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM dim_stock_group) AS groups,
                (SELECT COUNT(*) FROM dim_uom) AS uoms,
                (SELECT COUNT(*) FROM dim_item WHERE parent_name IS NOT NULL) AS items,
                (SELECT COUNT(DISTINCT brand) FROM dim_item WHERE brand IS NOT NULL) AS brands
        """)
        counts = cur.fetchone()
        
        # Get sample groups (roots and children)
        cur.execute("""
            SELECT g.name AS root, c.name AS child
            FROM dim_stock_group g
            LEFT JOIN dim_stock_group c ON c.parent_name = g.name
            WHERE g.parent_name IS NULL
            ORDER BY g.name, c.name
            LIMIT %s
        """, (limit,))
        group_tree = cur.fetchall()
        
        # Get sample items (if any)
        cur.execute("""
            SELECT brand, name, uom, hsn
            FROM dim_item
            WHERE parent_name IS NOT NULL
            ORDER BY brand NULLS LAST, name
            LIMIT %s
        """, (limit,))
        items_sample = cur.fetchall()
    
    return {
        "counts": {
            "groups": counts[0] if counts else 0,
            "uoms": counts[1] if counts else 0,
            "items": counts[2] if counts else 0,
            "brands": counts[3] if counts else 0,
        },
        "group_tree": group_tree,
        "items_sample": items_sample,
    }


def _compute_group_roots(groups: list[dict]) -> dict[str, str | None]:
    """Build a mapping of group -> root group name (None if no chain).

    Resolves parent chains in-memory so we can filter by requested brands before DB upsert.
    """
    name_to_parent: dict[str, str | None] = {g["name"]: g["parent_name"] for g in groups}

    cache: dict[str, str | None] = {}

    def root_of(name: str) -> str | None:
        if name in cache:
            return cache[name]
        seen: set[str] = set()
        cur = name
        while True:
            if cur in seen:
                # Cycle detected; treat as no root
                cache[name] = None
                return None
            seen.add(cur)
            parent = name_to_parent.get(cur)
            if not parent:
                cache[name] = cur
                return cur
            cur = parent

    for g in groups:
        cache[g["name"]] = root_of(g["name"])  # fill cache
    return cache


def _filter_by_brands(groups: list[dict], items: list[dict], brand_names: list[str]) -> tuple[list[dict], list[dict]]:
    """Filter groups and items to only those under specified root brands.

    - Keeps root groups that match, and any descendants whose root resolves to a matched root.
    - For items, keeps those whose parent group resolves to one of the matched roots.
    """
    if not brand_names:
        return groups, items

    roots_map = _compute_group_roots(groups)
    brand_set = {b.strip().lower() for b in brand_names if b.strip()}

    def is_group_kept(g: dict) -> bool:
        root = roots_map.get(g["name"]) or ""
        return root.strip().lower() in brand_set

    kept_groups = [g for g in groups if is_group_kept(g)]

    parent_to_root = {name: root for name, root in roots_map.items()}

    def is_item_kept(it: dict) -> bool:
        parent = (it.get("parent_name") or "").strip()
        root = (parent_to_root.get(parent) or "").strip().lower()
        return root in brand_set

    kept_items = [it for it in items if is_item_kept(it)]
    return kept_groups, kept_items


def export_to_csv(conn, csv_path: str):
    """Export items with brands to CSV."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT brand, name, sku, uom, hsn, parent_name
            FROM dim_item
            WHERE parent_name IS NOT NULL
            ORDER BY brand NULLS LAST, name
        """)
        rows = cur.fetchall()
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["brand", "name", "sku", "uom", "hsn", "parent_group"])
        writer.writerows(rows)
    
    logger.success(f"Exported {len(rows)} items to {csv_path}")


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
    export_csv_path = None
    brands_filter: list[str] = []
    
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
        elif arg == "--export-csv" and i + 1 < len(sys.argv):
            export_csv_path = sys.argv[i + 1]
            i += 2
        elif arg == "--brands" and i + 1 < len(sys.argv):
            brands_filter = [s for s in sys.argv[i + 1].split(",")]
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
        logger.info(f"Fetching masters from Tally: {TALLY_COMPANY}")
        xml_text = fetch_masters_from_tally(TALLY_COMPANY)
        # Debug: save the raw response so we can inspect the structure if parsing yields 0 rows
        try:
            debug_path = Path("tally_masters_response.xml")
            debug_path.write_text(xml_text, encoding="utf-8")
            logger.info(f"Saved Tally response to {debug_path} (size={len(xml_text)} chars)")
        except Exception as _e:
            # Non-fatal
            logger.debug(f"Could not write debug XML: {_e}")
    
    # Parse
    logger.info("Parsing masters XML...")
    data = parse_masters(xml_text)
    if brands_filter:
        original_counts = (len(data['groups']), len(data['items']))
        data['groups'], data['items'] = _filter_by_brands(data['groups'], data['items'], brands_filter)
        logger.info(f"Applied brand filter: {', '.join(brands_filter)}")
        logger.info(f"Groups/items before filter: {original_counts[0]}/{original_counts[1]} | after: {len(data['groups'])}/{len(data['items'])}")
    
    logger.info(f"Parsed: {len(data['units'])} units, {len(data['groups'])} groups, {len(data['items'])} items")
    
    # Show what would be loaded
    if data['groups']:
        root_groups = [g for g in data['groups'] if not g['parent_name']]
        logger.info(f"Found {len(root_groups)} root groups (brands):")
        for g in root_groups[:10]:  # Show first 10
            logger.info(f"  - {g['name']}")
        if len(root_groups) > 10:
            logger.info(f"  ... and {len(root_groups) - 10} more")
    
    if dry_run:
        logger.warning("DRY RUN MODE - No data will be written to database")
        logger.info("\n=== Preview (dry-run) ===")
        logger.info(f"Would upsert {len(data['units'])} units")
        logger.info(f"Would upsert {len(data['groups'])} groups")
        logger.info(f"Would upsert {len(data['items'])} items")
        
        if data['items']:
            logger.info("\nSample items (first 5):")
            for item in data['items'][:5]:
                logger.info(f"  {item['name']} (group: {item['parent_name']}, uom: {item['base_units']}, hsn: {item['hsn']})")
        else:
            logger.info("\nNo stock items found in XML (only groups/units)")
            logger.info("Tip: Use 'List of Stock Items' export to get item data")
        
        return
    
    # Connect to DB and load data
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        logger.info("Ensuring schema exists...")
        ensure_schema(conn)
        
        logger.info("Upserting units...")
        units_ins, units_upd = upsert_units(conn, data['units'])
        logger.success(f"Units: {units_ins} inserted, {units_upd} updated")
        
        logger.info("Upserting stock groups...")
        groups_ins, groups_upd = upsert_groups(conn, data['groups'])
        logger.success(f"Groups: {groups_ins} inserted, {groups_upd} updated")
        
        if data['items']:
            logger.info("Upserting stock items...")
            items_ins, items_upd = upsert_items(conn, data['items'])
            logger.success(f"Items: {items_ins} inserted, {items_upd} updated")
            
            logger.info("Computing brands (root groups)...")
            compute_brands(conn)
        else:
            logger.info("No stock items in XML - skipping item upsert")
        
        # Preview
        logger.info("\n=== Preview ===")
        preview = preview_data(conn, preview_limit)
        
        logger.info(f"\nTotals:")
        logger.info(f"  Stock Groups: {preview['counts']['groups']}")
        logger.info(f"  UOMs: {preview['counts']['uoms']}")
        logger.info(f"  Items: {preview['counts']['items']}")
        logger.info(f"  Distinct Brands: {preview['counts']['brands']}")
        
        if preview['items_sample']:
            logger.info(f"\nSample Items (first {min(len(preview['items_sample']), preview_limit)}):")
            for row in preview['items_sample'][:10]:
                brand, name, uom, hsn = row
                logger.info(f"  {brand or '(no brand)'} | {name} | {uom or ''} | {hsn or ''}")
        else:
            logger.info(f"\nRoot Groups (brands) and children:")
            current_root = None
            for row in preview['group_tree'][:20]:
                root, child = row
                if root != current_root:
                    logger.info(f"  [{root}]")
                    current_root = root
                if child:
                    logger.info(f"    - {child}")
        
        # Export CSV if requested
        if export_csv_path:
            logger.info(f"\nExporting to CSV: {export_csv_path}")
            export_to_csv(conn, export_csv_path)
        
        # Final checklist
        logger.info("\n=== Developer Checklist ===")
        if data['items']:
            logger.success(f"✓ Stock items found and loaded ({preview['counts']['items']} items)")
        else:
            logger.warning("⚠ No stock items in this XML")
            logger.info("  Suggestion: Export 'List of Stock Items' from Tally for item data")
        
        logger.info(f"✓ Distinct brands (root groups): {preview['counts']['brands']}")
        
        # Check for orphaned items (items whose parent group is missing)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM dim_item i
                WHERE i.parent_name IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM dim_stock_group g WHERE g.name = i.parent_name
                  )
            """)
            orphaned = cur.fetchone()[0]
            if orphaned > 0:
                logger.warning(f"⚠ {orphaned} items have missing parent groups (brand cannot be computed)")


if __name__ == "__main__":
    main()

