import json
import os
from datetime import datetime
from src.core.config import config

def save_pipeline_audit(total_bls: int, fast_path_matches: int, rejected_by_prefilter: int, sent_to_vector: int, sent_to_llm: int):
    audit_path = config['paths']['audit_log']
    
    vector_rejected = sent_to_vector - sent_to_llm
    
    audit_data = {
        "timestamp": datetime.now().isoformat(),
        "total_bls": total_bls,
        "fast_path_matches": fast_path_matches,
        "rejected_by_prefilter": rejected_by_prefilter,
        "sent_to_vector_search": sent_to_vector,
        "vector_search_rejected": vector_rejected,
        "sent_to_llm": sent_to_llm
    }
    
    # Save to a running log
    try:
        if os.path.exists(audit_path):
            with open(audit_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        history.append(audit_data)
        
        with open(audit_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
            
        print(f"📊 Audit Log Updated:")
        print(f"   -> {sent_to_vector} records went into Vector Search.")
        print(f"   -> {vector_rejected} records were mathematically impossible (Blocked).")
        print(f"   -> ONLY {sent_to_llm} records actually sent to the LLM!")
    except Exception as e:
        print(f"⚠️ Could not save audit log: {e}")