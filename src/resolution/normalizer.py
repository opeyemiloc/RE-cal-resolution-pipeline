import re

def normalize_name(name: str) -> str:
    """
    Cleans a messy company name for highly accurate mathematical and exact matching.
    """
    if not name:
        return ""
        
    # 1. Uppercase everything
    n = name.upper()
    
    # 2. Remove punctuation (commas, periods, hyphens)
    n = n.replace(".", "").replace(",", "").replace("-", " ")
    
    # 3. Expand common abbreviations (using word boundaries \b so we don't ruin actual words)
    n = re.sub(r'\bLTD\b', 'LIMITED', n)
    n = re.sub(r'\bIND\b', 'INDUSTRIES', n)
    n = re.sub(r'\bNIG\b', 'NIGERIA', n)
    n = re.sub(r'\bCO\b', 'COMPANY', n)
    n = re.sub(r'\bINTL\b', 'INTERNATIONAL', n)
    
    # 4. Remove extra/double spaces and strip ends
    n = " ".join(n.split())
    
    return n.strip()