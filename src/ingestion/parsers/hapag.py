import pandas as pd
from typing import List
from src.core.models import ShippingRecord
from src.core.config import config

def parse_hapag_excel(file_path: str) -> List[ShippingRecord]:
    """
    Reads a Hapag-Lloyd Container Arrival List (Excel).
    Strictly skips the first 4 rows of metadata (Ship Name, ETA, etc.)
    and expects exact column headers.
    """
    # 1. Read the Excel file, skipping exactly 7 rows of metadata
    #    Rows 0-6 contain: empty rows, title, ship name, agent, ETA info
    #    Row 7 is the actual header row (B/L NO, CONTAINER NO, CONSIGNEE, etc.)
    try:
        df = pd.read_excel(file_path, skiprows=7)
    except Exception as e:
        raise ValueError(f"Failed to read Hapag-Lloyd Excel file. Error: {e}")
    
    # 2. Clean column names (strip accidental whitespace from headers)
    df.columns = df.columns.str.strip()
    
    # Drop any fully-empty leading columns (Hapag files often have a blank column 0)
    df = df.loc[:, ~df.columns.str.startswith('Unnamed')]
    
    # 3. STRICT SAFETY CHECK: Fail loudly if Hapag changed their column names
    expected_columns = ['B/L NO', 'CONTAINER NO', 'CONSIGNEE']
    for col in expected_columns:
        if col not in df.columns:
            raise ValueError(
                f"❌ Hapag parser failed: Missing expected column '{col}'. "
                f"Columns found in file: {list(df.columns)}. Did Hapag change their format?"
            )
            
    # Drop empty trailing rows
    df = df.dropna(subset=['CONTAINER NO'])
    
    records: List[ShippingRecord] = []
    
    BANK_KEYWORDS = config['business_logic']['bank_keywords']
    JUNK_PATTERNS = config['business_logic']['junk_patterns']
    
    # 4. Iterate and map to Universal Schema
    for _, row in df.iterrows():
        vessel = str(row.get('VesselID', '')).strip() if 'VesselID' in df.columns and pd.notna(row.get('VesselID')) else None
        container = str(row.get('CONTAINER NO', '')).strip()
        bl_number = str(row.get('B/L NO', '')).strip()
        
        consignee = str(row.get('CONSIGNEE', '')).strip() if pd.notna(row.get('CONSIGNEE')) else ""
        notify = str(row.get('NOTIFY PARTY', '')).strip() if 'NOTIFY PARTY' in df.columns and pd.notna(row.get('NOTIFY PARTY')) else ""
        
        consignee_upper = consignee.upper()
        notify_upper = notify.upper()
        
        is_bank_consignee = any(keyword in consignee_upper for keyword in BANK_KEYWORDS)
        is_junk_consignee = any(j in consignee_upper for j in JUNK_PATTERNS)
        
        messy_name = consignee
        party_role = "Consignee"
        
        # Salvage Mission: If Consignee is TO ORDER / BANK / EMPTY, check Notify Party
        if not consignee or is_bank_consignee or is_junk_consignee:
            if notify and notify_upper not in ["SAME AS CONSIGNEE", "TO ORDER", ""]:
                messy_name = notify
                party_role = "Notify Party"
            else:
                # Strip junk from Consignee if Notify is useless
                cleaned_name = consignee_upper
                for word in ["TO THE ORDER OF", "TO ORDER OF", "TO THE ORDER", "TO ORDER", "BANK"]:
                    cleaned_name = cleaned_name.replace(word, "")
                cleaned_name = cleaned_name.strip(" ,.-")
                
                if cleaned_name:
                    messy_name = cleaned_name
                    party_role = "Salvaged Consignee"
                else:
                    messy_name = "UNKNOWN"
                    party_role = "Unknown"
        
        if not messy_name:
            messy_name = "UNKNOWN"

        records.append(
            ShippingRecord(
                shipping_line="HAPAG-LLOYD",
                vessel_name=vessel,
                container_number=container,
                bill_of_lading=bl_number,
                messy_party_name=messy_name,
                party_role=party_role
            )
        )
            
    return records