import os
from typing import List
from src.core.models import ShippingRecord
from src.ingestion.parsers.msc import parse_msc_excel
from src.ingestion.parsers.hapag import parse_hapag_excel
from src.ingestion.parsers.one import parse_one_excel
from src.ingestion.parsers.cosco import parse_cosco_excel
from src.core.config import config

# Maps config routing keys to their parser functions
PARSER_REGISTRY = {
    "one": ("ONE", parse_one_excel),
    "cosco": ("COSCO", parse_cosco_excel),
    "hapag": ("HAPAG-LLOYD", parse_hapag_excel),
    "msc": ("MSC", parse_msc_excel),
}

def parse_shipping_file(file_path: str) -> List[ShippingRecord]:
    """
    The Gatekeeper: Reads the filename and routes it to the correct shipping line parser.
    Returns a standardized list of ShippingRecord objects.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Could not find the file: {file_path}")

    # Extract the filename and make it lowercase for easy matching
    filename = os.path.basename(file_path).lower()
    
    # Safely get the routing rules from config.yaml
    routing_rules = config.get('routing', {})

    # Route based on keywords in the config file
    for carrier_key, (carrier_name, parser_fn) in PARSER_REGISTRY.items():
        keywords = routing_rules.get(carrier_key, [])
        if any(keyword in filename for keyword in keywords):
            print(f"🚢 Routing '{filename}' to {carrier_name} Parser...")
            return parser_fn(file_path)
    
    raise ValueError(
        f"❌ Error: Could not determine the shipping line for file '{filename}'. "
        "Please add a matching keyword to the 'routing' section in config.yaml."
    )