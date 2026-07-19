import os
from typing import List
from src.core.models import ShippingRecord
from src.ingestion.parsers.msc import parse_msc_excel
from src.ingestion.parsers.hapag import parse_hapag_excel
from src.core.config import config

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
    if any(keyword in filename for keyword in routing_rules.get('hapag', [])):
        print(f"🚢 Routing '{filename}' to Hapag-Lloyd Parser...")
        return parse_hapag_excel(file_path)

    elif any(keyword in filename for keyword in routing_rules.get('msc', [])):
        print(f"🚢 Routing '{filename}' to MSC Parser...")
        return parse_msc_excel(file_path)
        
    else:
        raise ValueError(
            f"❌ Error: Could not determine the shipping line for file '{filename}'. "
            "Please add a matching keyword to the 'routing' section in config.yaml."
        )