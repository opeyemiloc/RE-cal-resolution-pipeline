import re
from src.core.config import config

def resolve_party_name(consignee: str, notify: str) -> tuple[str, str]:
    """
    Shared salvage logic: determines the best party name from consignee/notify fields.
    Returns (messy_name, party_role).
    """
    BANK_KEYWORDS = config['business_logic']['bank_keywords']
    JUNK_PATTERNS = config['business_logic']['junk_patterns']
    
    consignee_upper = consignee.upper()
    notify_upper = notify.upper()
    
    is_bank_consignee = any(keyword in consignee_upper for keyword in BANK_KEYWORDS)
    is_junk_consignee = any(j in consignee_upper for j in JUNK_PATTERNS)
    
    messy_name = consignee
    party_role = "Consignee"
    
    if not consignee or is_bank_consignee or is_junk_consignee:
        if notify and notify_upper not in ["SAME AS CONSIGNEE", "TO ORDER", ""]:
            messy_name = notify
            party_role = "Notify Party"
        else:
            cleaned_name = consignee_upper
            for word in ["TO THE ORDER OF", "TO ORDER OF", "TO THE ORDER", "TO ORDER"]:
                cleaned_name = cleaned_name.replace(word, "")
            cleaned_name = re.sub(r'\bBANK\b', '', cleaned_name)
            cleaned_name = cleaned_name.strip(" ,.-")
            
            if cleaned_name:
                messy_name = cleaned_name
                party_role = "Salvaged Consignee"
            else:
                messy_name = "UNKNOWN"
                party_role = "Unknown"
    
    if not messy_name:
        messy_name = "UNKNOWN"
    
    return messy_name, party_role
