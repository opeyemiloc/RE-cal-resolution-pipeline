import json
import faiss
from typing import List, Tuple, Dict, Any
from sentence_transformers import SentenceTransformer
from src.core.models import ShippingRecord, ResolutionCandidate
from src.resolution.normalizer import normalize_name
from src.core.config import config

QUALITY_THRESHOLD = config['thresholds']['vector_quality_threshold']

def find_top_candidates(records: List[ShippingRecord], master_accounts_path: str) -> Tuple[List[ResolutionCandidate], List[Dict[str, Any]]]:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    master_accounts = json.load(open(master_accounts_path, 'r'))
    
    # EMBED THE NORMALIZED MASTER NAMES
    clean_master_names = [normalize_name(acc) for acc in master_accounts]
    master_embeddings = model.encode(clean_master_names)
    
    dimension = master_embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(master_embeddings)
    
    candidates: List[ResolutionCandidate] = []
    math_debug_log: List[Dict[str, Any]] = []
    
    for record in records:
        # EMBED THE NORMALIZED MESSY NAME
        clean_messy = normalize_name(record.messy_party_name)
        messy_vector = model.encode([clean_messy])
        distances, indices = index.search(messy_vector, k=3)
        
        best_distance = float(distances[0][0])
        # We still return the original master names to the AI
        top_names = [master_accounts[i] for i in indices[0]]
        all_distances = [float(d) for d in distances[0]]
        
        passed_threshold = best_distance <= QUALITY_THRESHOLD
        
        math_debug_log.append({
            "original_messy_name": record.messy_party_name,
            "normalized_messy_name": clean_messy,
            "best_match_name": top_names[0],
            "best_match_distance": round(best_distance, 4),
            "threshold_limit": QUALITY_THRESHOLD,
            "passed_gatekeeper": passed_threshold,
            "top_3_candidates": top_names,
            "top_3_distances": [round(d, 4) for d in all_distances]
        })
        
        if not passed_threshold:
            continue
            
        candidates.append(ResolutionCandidate(
            messy_name=record.messy_party_name, # keep original for output tracking
            candidate_master_names=top_names
        ))
        
    return candidates, math_debug_log