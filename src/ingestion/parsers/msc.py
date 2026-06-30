import pandas as pd
from typing import List
from src.core.models import ShippingRecord
from src.core.config import config

def parse_msc_excel(file_path: str) -> List[ShippingRecord]:
    """
    Reads an MSC Container Arrival List (Excel) and converts the rows
    into a standardized list of ShippingRecord objects.
    """
    # 1. Read the Excel file (skip 5 rows of metadata)
    try:
        df = pd.read_excel(file_path, skiprows=5)
    except Exception as e:
        raise ValueError(f"Failed to read MSC Excel file. Error: {e}")
    
    # 2. Clean column names (strip accidental whitespace from headers)
    df.columns = df.columns.str.strip()
    
    # 3. Drop empty trailing rows (if there's no Container Number, it's not a real row)
    if 'Container Number' in df.columns:
        df = df.dropna(subset=['Container Number'])
    
    records: List[ShippingRecord] = []
    
    # Keywords that indicate a Letter of Credit / Bank instead of a real importer
    BANK_KEYWORDS = config['business_logic']['bank_keywords']
    # Load junk patterns from config to catch "TO ORDER"
    JUNK_PATTERNS = config['business_logic']['junk_patterns']
    
    # 4. Iterate through the dataframe and map to our Universal Schema
    for _, row in df.iterrows():
        # Safely extract text using the CORRECT MSC column names
        vessel = str(row.get('Vessel / Voyage', '')).strip() if pd.notna(row.get('Vessel / Voyage')) else None
        container = str(row.get('Container Number', '')).strip() if pd.notna(row.get('Container Number')) else None
        bl_number = str(row.get('Bill of Lading Number', '')).strip() if pd.notna(row.get('Bill of Lading Number')) else None
        
        consignee = str(row.get('Consignee Name', '')).strip() if pd.notna(row.get('Consignee Name')) else ""
        notify1 = str(row.get('Notify1 Name', '')).strip() if pd.notna(row.get('Notify1 Name')) else ""
        
        consignee_upper = consignee.upper()
        notify1_upper = notify1.upper()
        
        # Check if the Consignee is a bank OR contains "TO ORDER" / junk
        is_bank_consignee = any(keyword in consignee_upper for keyword in BANK_KEYWORDS)
        is_junk_consignee = any(j in consignee_upper for j in JUNK_PATTERNS)
        
        messy_name = consignee
        party_role = "Consignee"
        
        # If Consignee is empty, a bank, or "TO ORDER", we need to handle it
        if not consignee or is_bank_consignee or is_junk_consignee:
            # 1. Try to use Notify1 first (if it's valid)
            if notify1 and notify1_upper not in ["SAME AS CONSIGNEE", "TO ORDER", ""]:
                messy_name = notify1
                party_role = "Notify Party"
            else:
                # 2. SALVAGE MISSION: If Notify is useless, strip the junk from Consignee!
                # E.g., "TO ORDER OF JUDE EKELEDO" -> "JUDE EKELEDO"
                cleaned_name = consignee_upper
                for word in ["TO THE ORDER OF", "TO ORDER OF", "TO THE ORDER", "TO ORDER", "BANK"]:
                    cleaned_name = cleaned_name.replace(word, "")
                
                cleaned_name = cleaned_name.strip(" ,.-") # Clean up leftover spaces/punctuation
                
                if cleaned_name:
                    messy_name = cleaned_name
                    party_role = "Salvaged Consignee"
                else:
                    messy_name = "UNKNOWN"
                    party_role = "Unknown"
        
        # Fallback safeguard
        if not messy_name:
            messy_name = "UNKNOWN"

        records.append(
            ShippingRecord(
                shipping_line="MSC",
                vessel_name=vessel,
                container_number=container,
                bill_of_lading=bl_number,
                messy_party_name=messy_name,
                party_role=party_role
            )
        )
            
    return records