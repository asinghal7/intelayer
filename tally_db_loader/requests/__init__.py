"""
XML request templates for Tally API.

Templates are Jinja2 files that render XML requests for the Tally HTTP API.
"""
from pathlib import Path

# Template directory
TEMPLATE_DIR = Path(__file__).parent

# Available templates
TEMPLATES = {
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
    "vouchers": "vouchers.xml.j2",
    "vouchers_detailed": "vouchers_detailed.xml.j2",
    "closing_stock": "closing_stock.xml.j2",
}


def get_template_path(name: str) -> Path:
    """Get path to a template file."""
    if name not in TEMPLATES:
        raise ValueError(f"Unknown template: {name}. Valid: {list(TEMPLATES.keys())}")
    return TEMPLATE_DIR / TEMPLATES[name]


def load_template(name: str) -> str:
    """Load template contents."""
    return get_template_path(name).read_text(encoding="utf-8")

