import pandas as pd
from typing import List
from src.core.models import ShippingRecord
from src.core.config import config

def parse_cosco_excel(file_path: str) -> List[ShippingRecord]:
    """
    Reads a COSCO Container Arrival List (Excel).
    
    File structure:
      Row 0:  Column headers (S/N, BL Number, Port Of Loading, ..., Consignee Name, NOTIFY, Container ID, etc.)
      Row 1+: Actual data
    
    This file is clean — no metadata block to skip.
    """
    # 1. Read the Excel file (no skiprows needed, headers are on row 0)
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read COSCO Excel file. Error: {e}")
    
    # 2. Clean column names
    df.columns = df.columns.str.strip()
    
    # 3. STRICT SAFETY CHECK
    expected_columns = ['BL Number', 'Container ID', 'Consignee Name']
    for col in expected_columns:
        if col not in df.columns:
            raise ValueError(
                f"❌ COSCO parser failed: Missing expected column '{col}'. "
                f"Columns found in file: {list(df.columns)}. Did COSCO change their format?"
            )
    
    # Drop empty trailing rows
    df = df.dropna(subset=['Container ID'])
    
    records: List[ShippingRecord] = []
    
    BANK_KEYWORDS = config['business_logic']['bank_keywords']
    JUNK_PATTERNS = config['business_logic']['junk_patterns']
    
    # 4. Iterate and map to Universal Schema
    for _, row in df.iterrows():
        bl_number = str(row.get('BL Number', '')).strip() if pd.notna(row.get('BL Number')) else None
        container = str(row.get('Container ID', '')).strip() if pd.notna(row.get('Container ID')) else None
        
        consignee = str(row.get('Consignee Name', '')).strip() if pd.notna(row.get('Consignee Name')) else ""
        notify = str(row.get('NOTIFY', '')).strip() if 'NOTIFY' in df.columns and pd.notna(row.get('NOTIFY')) else ""
        
        # Extract port fields if available
        pol = str(row.get('Port Of Loading', '')).strip() if 'Port Of Loading' in df.columns and pd.notna(row.get('Port Of Loading')) else None
        pod = str(row.get('Port Of Destination', '')).strip() if 'Port Of Destination' in df.columns and pd.notna(row.get('Port Of Destination')) else None
        
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
                shipping_line="COSCO",
                vessel_name=None,  # Vessel name is typically in the filename for COSCO
                container_number=container,
                bill_of_lading=bl_number,
                messy_party_name=messy_name,
                party_role=party_role,
                port_of_discharge=pod,
            )
        )
            
    return records
