import pandas as pd
from typing import List
from src.core.models import ShippingRecord
from src.core.config import config
from src.ingestion.parsers.common import resolve_party_name

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
    
    # STRICT SAFETY CHECK
    expected_columns = ['Bill of Lading Number', 'Container Number', 'Consignee Name']
    for col in expected_columns:
        if col not in df.columns:
            raise ValueError(
                f"❌ MSC parser failed: Missing expected column '{col}'. "
                f"Columns found in file: {list(df.columns)}. Did MSC change their format?"
            )
    
    # 3. Drop empty trailing rows (if there's no Container Number, it's not a real row)
    if 'Container Number' in df.columns:
        df = df.dropna(subset=['Container Number'])
    
    records: List[ShippingRecord] = []
    
    # 4. Iterate through the dataframe and map to our Universal Schema
    for _, row in df.iterrows():
        # Safely extract text using the CORRECT MSC column names
        vessel = str(row.get('Vessel / Voyage', '')).strip() if pd.notna(row.get('Vessel / Voyage')) else None
        container = str(row.get('Container Number', '')).strip() if pd.notna(row.get('Container Number')) else None
        bl_number = str(row.get('Bill of Lading Number', '')).strip() if pd.notna(row.get('Bill of Lading Number')) else None
        
        # Port of Discharge
        pod_raw = row.get('Port of Discharge')
        pod = str(pod_raw).strip() if pd.notna(pod_raw) else None
        
        # ETA
        eta_raw = row.get('ETA')
        eta = str(eta_raw).strip() if pd.notna(eta_raw) else None
        
        consignee = str(row.get('Consignee Name', '')).strip() if pd.notna(row.get('Consignee Name')) else ""
        notify1 = str(row.get('Notify1 Name', '')).strip() if pd.notna(row.get('Notify1 Name')) else ""
        
        messy_name, party_role = resolve_party_name(consignee, notify1)

        records.append(
            ShippingRecord(
                shipping_line="MSC",
                vessel_name=vessel,
                container_number=container,
                bill_of_lading=bl_number,
                messy_party_name=messy_name,
                party_role=party_role,
                port_of_discharge=pod,
                eta=eta,
            )
        )
            
    return records