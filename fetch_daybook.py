#!/usr/bin/env python3
"""
Tally Daybook Voucher Counter
Fetches daybook report from Tally via XML API and counts vouchers for a specified date.
"""

import argparse
import configparser
import datetime
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple

import requests


class TallyDaybookFetcher:
    """Handles fetching and parsing daybook data from Tally."""
    
    def __init__(self, tally_url: str, company_name: str):
        """
        Initialize the Tally Daybook Fetcher.
        
        Args:
            tally_url: URL of the Tally server (e.g., http://192.168.0.189:9000)
            company_name: Name of the company in Tally
        """
        self.tally_url = tally_url
        self.company_name = company_name
    
    def construct_xml_request(self, date: str) -> str:
        """
        Construct XML request for daybook report.
        
        Args:
            date: Date in YYYYMMDD format
            
        Returns:
            XML request string
        """
        xml_request = f"""<ENVELOPE>
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
        <SVCURRENTCOMPANY>{self.company_name}</SVCURRENTCOMPANY>
        <SVFROMDATE TYPE="Date">{date}</SVFROMDATE>
        <SVTODATE TYPE="Date">{date}</SVTODATE>
        <EXPLODEFLAG>Yes</EXPLODEFLAG>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""
        return xml_request
    
    def fetch_daybook(self, date: str, timeout: int = 30) -> str:
        """
        Fetch daybook data from Tally server.
        
        Args:
            date: Date in YYYYMMDD format
            timeout: Request timeout in seconds
            
        Returns:
            XML response string
            
        Raises:
            requests.RequestException: If request fails
        """
        xml_request = self.construct_xml_request(date)
        
        try:
            response = requests.post(
                self.tally_url,
                data=xml_request.encode('utf-8'),
                timeout=timeout,
                headers={'Content-Type': 'application/xml'}
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.ConnectionError as e:
            raise requests.RequestException(
                f"Failed to connect to Tally server at {self.tally_url}. "
                "Please ensure Tally is running and ODBC server is enabled."
            ) from e
        except requests.exceptions.Timeout as e:
            raise requests.RequestException(
                f"Request to Tally server timed out after {timeout} seconds."
            ) from e
        except requests.exceptions.HTTPError as e:
            raise requests.RequestException(
                f"HTTP error occurred: {e.response.status_code} - {e.response.reason}"
            ) from e
    
    def sanitize_xml(self, xml_string: str) -> str:
        """
        Sanitize XML string by removing invalid characters and character references.
        
        Args:
            xml_string: Raw XML string
            
        Returns:
            Sanitized XML string
        """
        import re
        
        # First, remove invalid character entity references like &#x0; &#x1F; etc.
        # These are XML entities that reference invalid characters
        xml_string = re.sub(r'&#x([0-8bcefBCEF]|1[0-9a-fA-F]);', '', xml_string)
        xml_string = re.sub(r'&#([0-9]|1[0-9]|2[0-6]|3[01]);', '', xml_string)
        
        # Then remove raw invalid XML characters (control characters except tab, newline, carriage return)
        # Valid XML chars: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
        invalid_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x84\x86-\x9F]')
        xml_string = invalid_chars.sub('', xml_string)
        
        return xml_string
    
    def parse_voucher_count(self, xml_response: str) -> Tuple[int, list]:
        """
        Parse XML response and count vouchers.
        
        Args:
            xml_response: XML response string from Tally
            
        Returns:
            Tuple of (voucher_count, list of voucher details)
            
        Raises:
            ET.ParseError: If XML parsing fails
        """
        try:
            # Sanitize XML to remove invalid characters
            sanitized_xml = self.sanitize_xml(xml_response)
            root = ET.fromstring(sanitized_xml)
            
            # Check for error in response
            error_elem = root.find('.//ERROR')
            if error_elem is not None:
                error_msg = error_elem.text or "Unknown error from Tally"
                raise ValueError(f"Tally returned an error: {error_msg}")
            
            # Find all VOUCHER elements
            vouchers = root.findall('.//VOUCHER')
            
            # Extract basic voucher information
            voucher_details = []
            for voucher in vouchers:
                voucher_type = voucher.find('.//VOUCHERTYPENAME')
                voucher_number = voucher.find('.//VOUCHERNUMBER')
                party_name = voucher.find('.//PARTYLEDGERNAME')
                amount = voucher.find('.//AMOUNT')
                
                detail = {
                    'type': voucher_type.text if voucher_type is not None else 'N/A',
                    'number': voucher_number.text if voucher_number is not None else 'N/A',
                    'party': party_name.text if party_name is not None else 'N/A',
                    'amount': amount.text if amount is not None else 'N/A'
                }
                voucher_details.append(detail)
            
            return len(vouchers), voucher_details
            
        except ET.ParseError as e:
            # Save the problematic XML for debugging
            try:
                Path('error_response.xml').write_text(xml_response, encoding='utf-8', errors='replace')
                Path('error_response_sanitized.xml').write_text(sanitized_xml, encoding='utf-8', errors='replace')
                error_msg = (
                    f"Failed to parse XML response from Tally. "
                    f"Error: {str(e)}\n"
                    f"Raw response saved to: error_response.xml\n"
                    f"Sanitized response saved to: error_response_sanitized.xml"
                )
            except:
                error_msg = f"Failed to parse XML response from Tally. Error: {str(e)}"
            raise ET.ParseError(error_msg) from e


def load_config(config_file: Path) -> dict:
    """
    Load configuration from file.
    
    Args:
        config_file: Path to config file
        
    Returns:
        Dictionary of configuration values
    """
    config = configparser.ConfigParser()
    
    if config_file.exists():
        config.read(config_file)
        if 'tally' in config:
            return {
                'tally_url': config['tally'].get('url'),
                'company_name': config['tally'].get('company')
            }
    
    return {}


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='Fetch daybook report from Tally and count vouchers.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch today's daybook with config file
  python fetch_daybook.py --tally-url http://192.168.0.189:9000 --company "My Company"
  
  # Fetch for a specific date
  python fetch_daybook.py --tally-url http://192.168.0.189:9000 --company "My Company" --date 20251011
  
  # Use config file (config.ini)
  python fetch_daybook.py
        """
    )
    
    parser.add_argument(
        '--tally-url',
        type=str,
        help='Tally server URL (e.g., http://192.168.0.189:9000)'
    )
    
    parser.add_argument(
        '--company',
        type=str,
        help='Company name in Tally (must match exactly)'
    )
    
    parser.add_argument(
        '--date',
        type=str,
        default=datetime.date.today().strftime('%Y%m%d'),
        help='Date to fetch in YYYYMMDD format (default: today)'
    )
    
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('config.ini'),
        help='Path to configuration file (default: config.ini)'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show detailed voucher information'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Save raw XML response to debug.xml for troubleshooting'
    )
    
    return parser.parse_args()


def validate_date(date_str: str) -> bool:
    """
    Validate date string format.
    
    Args:
        date_str: Date string in YYYYMMDD format
        
    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.datetime.strptime(date_str, '%Y%m%d')
        return True
    except ValueError:
        return False


def format_date_display(date_str: str) -> str:
    """
    Format date for display.
    
    Args:
        date_str: Date string in YYYYMMDD format
        
    Returns:
        Formatted date string (DD-MM-YYYY)
    """
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y%m%d')
        return date_obj.strftime('%d-%m-%Y')
    except ValueError:
        return date_str


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Load configuration from file
    config = load_config(args.config)
    
    # Command-line arguments override config file
    tally_url = args.tally_url or config.get('tally_url')
    company_name = args.company or config.get('company_name')
    
    # Validate required parameters
    if not tally_url:
        print("Error: Tally URL is required. Provide it via --tally-url or config.ini", file=sys.stderr)
        sys.exit(1)
    
    if not company_name:
        print("Error: Company name is required. Provide it via --company or config.ini", file=sys.stderr)
        sys.exit(1)
    
    # Validate date format
    if not validate_date(args.date):
        print(f"Error: Invalid date format '{args.date}'. Use YYYYMMDD format.", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Initialize fetcher
        fetcher = TallyDaybookFetcher(tally_url, company_name)
        
        print(f"Fetching daybook from Tally...")
        print(f"  Server: {tally_url}")
        print(f"  Company: {company_name}")
        print(f"  Date: {format_date_display(args.date)}")
        print()
        
        # Fetch daybook
        xml_response = fetcher.fetch_daybook(args.date, timeout=args.timeout)
        
        # Save debug output if requested
        if args.debug:
            debug_file = Path('debug.xml')
            debug_file.write_text(xml_response, encoding='utf-8')
            print(f"  Debug: Raw XML saved to {debug_file.absolute()}")
        
        # Parse and count vouchers
        voucher_count, voucher_details = fetcher.parse_voucher_count(xml_response)
        
        # Display results
        print(f"✓ Successfully fetched daybook report")
        print(f"  Total Vouchers: {voucher_count}")
        
        if args.verbose and voucher_details:
            print("\nVoucher Details:")
            print("-" * 80)
            for idx, voucher in enumerate(voucher_details, 1):
                print(f"{idx:3d}. Type: {voucher['type']:20s} | "
                      f"Number: {voucher['number']:15s} | "
                      f"Party: {voucher['party']:25s}")
            print("-" * 80)
        
        return 0
        
    except requests.RequestException as e:
        print(f"\n✗ Network Error: {e}", file=sys.stderr)
        return 1
    except ET.ParseError as e:
        print(f"\n✗ XML Parse Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

