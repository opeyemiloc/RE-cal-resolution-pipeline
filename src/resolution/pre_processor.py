from src.core.models import LLMMatchDecision

def should_reject(name: str) -> bool:
    """Returns True if the name is definitively junk or invalid."""
    n = name.upper().strip()
    junk_patterns = ["TO ORDER", "NULL", "UNKNOWN", "AS PER", "BANK", "LOC", "SAME AS"]
    
    # Logic: If it is too short or clearly junk, reject it before math starts.
    if len(n) < 4:
        return True
    
    return any(p in n for p in junk_patterns)

def create_rejection_decision(name: str) -> LLMMatchDecision:
    return LLMMatchDecision(
        original_messy_name=name,
        matched=False,
        resolved_master_name=None,
        confidence_score=0,
        reasoning="Rejected by Pre-filter: Junk name or invalid structure."
    )