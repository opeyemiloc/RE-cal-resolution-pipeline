import pandas as pd
from typing import List
from src.core.models import ShippingRecord
from src.core.config import config
from src.ingestion.parsers.common import resolve_party_name

def parse_one_excel(file_path: str) -> List[ShippingRecord]:
    """
    Reads a ONE (Ocean Network Express) Container Discharge List (Excel).
    
    File structure:
      Rows 0-7: Metadata (NPA header, vessel, agent, ETA info)
      Row 8-9:  Column headers split across two rows (e.g., 'B/L NO' on row 8, 'Serial No.' on row 9)
      Row 10+:  Actual data
    
    We skip 8 rows so pandas picks up the first header line,
    then drop the sub-header row (row 9) which contains things like 'Serial No.', '& No.' etc.
    """
    # 1. Read the Excel file, skipping 8 rows of metadata
    #    Row 8 becomes the header row (B/L NO, Cont. Prefix, Receiver, etc.)
    try:
        df = pd.read_excel(file_path, skiprows=8)
    except Exception as e:
        raise ValueError(f"Failed to read ONE Excel file. Error: {e}")
    
    # 2. Clean column names
    df.columns = df.columns.str.strip()
    
    # 3. Drop the sub-header row (row 9 in original, now row 0 in df)
    #    It contains things like 'Serial No.', '& No.' — not real data
    if len(df) > 0:
        first_row = df.iloc[0]
        first_row_str = " ".join(str(v) for v in first_row.values if pd.notna(v))
        if "Serial No" in first_row_str or "& No" in first_row_str:
            df = df.iloc[1:].reset_index(drop=True)
    
    # 4. Drop leading empty columns
    df = df.loc[:, ~df.columns.str.startswith('Unnamed')]
    
    # 5. STRICT SAFETY CHECK
    expected_columns = ['B/L NO', 'Cont. Prefix', 'Receiver']
    for col in expected_columns:
        if col not in df.columns:
            raise ValueError(
                f"❌ ONE parser failed: Missing expected column '{col}'. "
                f"Columns found in file: {list(df.columns)}. Did ONE change their format?"
            )
    
    # Drop empty trailing rows
    df = df.dropna(subset=['Cont. Prefix'])
    
    records: List[ShippingRecord] = []
    
    # 6. Iterate and map to Universal Schema
    for _, row in df.iterrows():
        bl_number = str(row.get('B/L NO', '')).strip() if pd.notna(row.get('B/L NO')) else None
        # Note: The column is confusingly named 'Cont. Prefix' but actually contains the FULL container ID.
        container = str(row.get('Cont. Prefix', '')).strip() if pd.notna(row.get('Cont. Prefix')) else None
        
        consignee = str(row.get('Receiver', '')).strip() if pd.notna(row.get('Receiver')) else ""
        notify = str(row.get('Notify Name', '')).strip() if 'Notify Name' in df.columns and pd.notna(row.get('Notify Name')) else ""
        
        messy_name, party_role = resolve_party_name(consignee, notify)


        records.append(
            ShippingRecord(
                shipping_line="ONE",
                vessel_name=None,  # Vessel is in metadata rows, not in data columns
                container_number=container,
                bill_of_lading=bl_number,
                messy_party_name=messy_name,
                party_role=party_role
            )
        )
            
    return records
