#!/usr/bin/env python3
"""
Load pincode data from CSV into dim_pincode table.

Usage:
    python load_pincode_data.py
"""

import csv
import psycopg
from loguru import logger
from pathlib import Path
from agent.settings import DB_URL

def load_pincode_data(csv_file: Path):
    """Load pincode data from CSV into database."""
    
    logger.info(f"Loading pincode data from {csv_file}")
    
    # Read and parse CSV
    pincodes = []
    duplicates = 0
    seen_pincodes = set()
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pincode = row['pincode'].strip()
            
            # Skip if we've already seen this pincode (keep first occurrence)
            if pincode in seen_pincodes:
                duplicates += 1
                continue
            
            seen_pincodes.add(pincode)
            
            # Extract required fields
            # Handle latitude/longitude (may be 'NA' or empty)
            try:
                lat = float(row['latitude']) if row['latitude'] and row['latitude'].upper() != 'NA' else None
            except (ValueError, AttributeError):
                lat = None
            
            try:
                lon = float(row['longitude']) if row['longitude'] and row['longitude'].upper() != 'NA' else None
            except (ValueError, AttributeError):
                lon = None
            
            pincodes.append({
                'pincode': pincode,
                'city': row['district'].strip().title() if row['district'] else None,
                'state': row['statename'].strip().title() if row['statename'] else None,
                'lat': lat,
                'lon': lon,
            })
    
    logger.info(f"Read {len(pincodes)} unique pincodes from CSV ({duplicates} duplicates skipped)")
    
    # Insert into database
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            # Clear existing data (optional - comment out if you want to keep existing data)
            # cur.execute("TRUNCATE TABLE dim_pincode")
            # logger.info("Cleared existing data from dim_pincode")
            
            # Insert data
            insert_count = 0
            update_count = 0
            
            for pc in pincodes:
                cur.execute("""
                    INSERT INTO dim_pincode (pincode, city, state, lat, lon)
                    VALUES (%(pincode)s, %(city)s, %(state)s, %(lat)s, %(lon)s)
                    ON CONFLICT (pincode) DO UPDATE SET
                        city = EXCLUDED.city,
                        state = EXCLUDED.state,
                        lat = EXCLUDED.lat,
                        lon = EXCLUDED.lon
                    RETURNING (xmax = 0) AS inserted
                """, pc)
                
                # Check if it was an insert or update
                result = cur.fetchone()
                if result and result[0]:
                    insert_count += 1
                else:
                    update_count += 1
            
            conn.commit()
    
    logger.success(f"✓ Loaded {insert_count} new pincodes, updated {update_count} existing pincodes")
    logger.info(f"Total pincodes in database: {len(pincodes)}")

def main():
    csv_file = Path(__file__).parent / "pincodemapvf.csv"
    
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_file}")
        return
    
    load_pincode_data(csv_file)

if __name__ == "__main__":
    main()

