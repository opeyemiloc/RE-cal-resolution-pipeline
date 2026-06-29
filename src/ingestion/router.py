import os
from typing import List
from src.core.models import ShippingRecord
from src.ingestion.parsers.msc import parse_msc_excel

def parse_shipping_file(file_path: str) -> List[ShippingRecord]:
    """
    The Gatekeeper: Reads the filename and routes it to the correct shipping line parser.
    Returns a standardized list of ShippingRecord objects.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Could not find the file: {file_path}")

    # Extract the filename and make it lowercase for easy matching
    filename = os.path.basename(file_path).lower()

    # Route based on keywords in the filename
    if "msc" in filename:
        print(f"🚢 Routing '{filename}' to MSC Parser...")
        return parse_msc_excel(file_path)
        
    elif "zim" in filename:
        print(f"🚢 Routing '{filename}' to ZIM Parser...")
        raise NotImplementedError("ZIM parser is not built yet.")
        
    elif "hapag" in filename:
        print(f"🚢 Routing '{filename}' to Hapag-Lloyd Parser...")
        raise NotImplementedError("Hapag-Lloyd parser is not built yet.")
        
    else:
        raise ValueError(
            f"❌ Error: Could not determine the shipping line for file '{filename}'. "
            "Please ensure the filename contains the carrier name (e.g., 'msc', 'zim')."
        )