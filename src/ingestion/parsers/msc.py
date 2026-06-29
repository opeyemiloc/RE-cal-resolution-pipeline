import pandas as pd
from typing import List
from src.core.models import ShippingRecord

def parse_msc_excel(file_path: str) -> List[ShippingRecord]:
    """
    Reads an MSC Container Arrival List (Excel) and converts the rows
    into a standardized list of ShippingRecord objects.
    """
    # 1. Read the Excel file. 
    # The MSC CAL has 5 rows of metadata at the top. 'skiprows=5' makes row 6 the header.
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
    BANK_KEYWORDS = ["BANK", "TO THE ORDER", "L/C", "LETTER OF CREDIT", "FINANCE"]
    
    # 4. Iterate through the dataframe and map to our Universal Schema
    for _, row in df.iterrows():
        # Safely extract text, converting Pandas NaNs to None/empty strings
        vessel = str(row.get('Vessel / Voyage', '')).strip() if pd.notna(row.get('Vessel / Voyage')) else None
        container = str(row.get('Container Number', '')).strip() if pd.notna(row.get('Container Number')) else None
        bl_number = str(row.get('Bill of Lading Number', '')).strip() if pd.notna(row.get('Bill of Lading Number')) else None
        
        consignee = str(row.get('Consignee Name', '')).strip() if pd.notna(row.get('Consignee Name')) else ""
        notify1 = str(row.get('Notify1 Name', '')).strip() if pd.notna(row.get('Notify1 Name')) else ""
        
        # Check if consignee is a bank / LOC
        is_bank_consignee = any(keyword in consignee.upper() for keyword in BANK_KEYWORDS)
        
        # Decide which party to use: Consignee first, fallback to Notify Party
        valid_consignee = bool(consignee and consignee.upper() != "TO ORDER" and not is_bank_consignee)
        
        if valid_consignee:
            # If Consignee is a real company, use it!
            records.append(
                ShippingRecord(
                    shipping_line="MSC",
                    vessel_name=vessel,
                    container_number=container,
                    bill_of_lading=bl_number,
                    messy_party_name=consignee,
                    party_role="Consignee"
                )
            )
        elif notify1 and notify1.upper() not in ["SAME AS CONSIGNEE", "TO ORDER"]:
            # ONLY use Notify Party if the Consignee was invalid
            records.append(
                ShippingRecord(
                    shipping_line="MSC",
                    vessel_name=vessel,
                    container_number=container,
                    bill_of_lading=bl_number,
                    messy_party_name=notify1,
                    party_role="Notify Party"
                )
            )
            
    return records