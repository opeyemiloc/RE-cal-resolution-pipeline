import json
from typing import List, Tuple
from src.core.models import ShippingRecord, LLMMatchDecision
from src.resolution.normalizer import normalize_name

# Define suffixes to strip for the second-pass "core brand" match.
# Note: normalizer.py already expands LTD->LIMITED, NIG->NIGERIA, etc.
SUFFIX_WORDS = {"LIMITED", "LTD", "PLC", "NIGERIA", "COMPANY", "INTERNATIONAL", "INDUSTRIES", "SL", "INC", "LTD."}

def strip_suffixes(name: str) -> str:
    """Removes common corporate suffixes to extract the core brand name."""
    tokens = [t for t in name.split() if t not in SUFFIX_WORDS]
    return " ".join(tokens)

def process_exact_matches(records: List[ShippingRecord], master_accounts_path: str) -> Tuple[List[LLMMatchDecision], List[ShippingRecord]]:
    with open(master_accounts_path, 'r') as f:
        master_accounts = json.load(f)
        
    # PASS 1: Standard Normalized Lookup
    # e.g., {"CYBELE COSMETICS LIMITED": "CYBELE COSMETICS LIMITED"}
    master_lookup = {normalize_name(acc): acc for acc in master_accounts}
    
    # PASS 2: Core Brand Lookup (Aggressive suffix stripping)
    # e.g., {"TOP STEEL": "TOP STEEL NIGERIA"}
    core_master_lookup = {}
    for acc in master_accounts:
        clean_acc = normalize_name(acc)
        core_acc = strip_suffixes(clean_acc)
        if core_acc: # Prevent empty string keys if a name is purely suffixes
            core_master_lookup[core_acc] = acc
    
    exact_matches, unmatched_records = [], []
    
    for record in records:
        # Clean the messy name before checking
        clean_messy = normalize_name(record.messy_party_name)
        
        # Check Pass 1 (Strict Normalized)
        if clean_messy in master_lookup:
            exact_matches.append(LLMMatchDecision(
                original_messy_name=record.messy_party_name, 
                matched=True,
                resolved_master_name=master_lookup[clean_messy], 
                confidence_score=100,
                reasoning="Exact match found after standardizing abbreviations and punctuation."
            ))
            continue
            
        # Check Pass 2 (Core Brand Match)
        # Strips extra suffixes to see if the root words align
        core_messy = strip_suffixes(clean_messy)
        if core_messy and core_messy in core_master_lookup:
            exact_matches.append(LLMMatchDecision(
                original_messy_name=record.messy_party_name, 
                matched=True,
                resolved_master_name=core_master_lookup[core_messy], 
                confidence_score=100,
                reasoning=f"Core brand match found (stripped suffixes to compare '{core_messy}')."
            ))
        else:
            unmatched_records.append(record)
            
    return exact_matches, unmatched_records