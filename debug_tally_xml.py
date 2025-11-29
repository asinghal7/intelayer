#!/usr/bin/env python3
"""
Debug script to fetch raw XML from Tally and save it for inspection.

This helps diagnose parsing issues by examining the actual XML structure
returned by Tally.

Usage:
    python debug_tally_xml.py groups
    python debug_tally_xml.py ledgers
    python debug_tally_xml.py company
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tally_db_loader.config import TallyLoaderConfig
from tally_db_loader.client import TallyLoaderClient
from tally_db_loader.sync import TallySync, REQUESTS_DIR
from jinja2 import Template


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_tally_xml.py <entity>")
        print("Entities: company, groups, ledgers, stock_groups, stock_items, units, godowns, etc.")
        sys.exit(1)
    
    entity = sys.argv[1]
    
    # Map entity to template
    templates = {
        "company": "company.xml.j2",
        "groups": "groups.xml.j2",
        "ledgers": "ledgers.xml.j2",
        "stock_groups": "stock_groups.xml.j2",
        "stock_categories": "stock_categories.xml.j2",
        "units": "units.xml.j2",
        "godowns": "godowns.xml.j2",
        "stock_items": "stock_items.xml.j2",
        "cost_categories": "cost_categories.xml.j2",
        "cost_centres": "cost_centres.xml.j2",
        "voucher_types": "voucher_types.xml.j2",
        "currencies": "currencies.xml.j2",
    }
    
    if entity not in templates:
        print(f"Unknown entity: {entity}")
        print(f"Valid entities: {list(templates.keys())}")
        sys.exit(1)
    
    config = TallyLoaderConfig.from_env()
    print(f"Tally URL: {config.tally_url}")
    print(f"Company: {config.tally_company}")
    
    # Load and render template
    template_path = REQUESTS_DIR / templates[entity]
    template_str = template_path.read_text(encoding="utf-8")
    template = Template(template_str)
    xml_request = template.render(company=config.tally_company)
    
    # Save request
    request_file = Path(f"debug_{entity}_request.xml")
    request_file.write_text(xml_request, encoding="utf-8")
    print(f"Saved request to: {request_file}")
    
    # Fetch from Tally
    client = TallyLoaderClient(config)
    print(f"Fetching {entity} from Tally...")
    
    try:
        xml_response = client.post_xml(xml_request)
        
        # Save raw response
        response_file = Path(f"debug_{entity}_response.xml")
        response_file.write_text(xml_response, encoding="utf-8")
        print(f"Saved response to: {response_file}")
        print(f"Response size: {len(xml_response)} bytes")
        
        # Show first 2000 chars
        print("\n=== First 2000 characters of response ===")
        print(xml_response[:2000])
        
        if len(xml_response) > 2000:
            print("\n... (truncated)")
        
    except Exception as e:
        print(f"Error fetching from Tally: {e}")
        sys.exit(1)
    
    client.close()


if __name__ == "__main__":
    main()

