import pandas as pd
from typing import List
from src.core.models import ShippingRecord
from src.core.config import config
from src.ingestion.parsers.common import resolve_party_name

def parse_hapag_excel(file_path: str) -> List[ShippingRecord]:
    """
    Reads a Hapag-Lloyd Container Arrival List (Excel).
    Strictly skips the first 7 rows of metadata (Ship Name, ETA, etc.)
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
    
    # 4. Iterate and map to Universal Schema
    for _, row in df.iterrows():
        vessel = str(row.get('VesselID', '')).strip() if 'VesselID' in df.columns and pd.notna(row.get('VesselID')) else None
        container = str(row.get('CONTAINER NO', '')).strip()
        bl_number = str(row.get('B/L NO', '')).strip()
        
        consignee = str(row.get('CONSIGNEE', '')).strip() if pd.notna(row.get('CONSIGNEE')) else ""
        notify = str(row.get('NOTIFY PARTY', '')).strip() if 'NOTIFY PARTY' in df.columns and pd.notna(row.get('NOTIFY PARTY')) else ""
        
        messy_name, party_role = resolve_party_name(consignee, notify)

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