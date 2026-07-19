import os
import json
from src.ingestion.router import parse_shipping_file
from src.ingestion.parsers.master_parser import ingest_master_list_excel
from src.resolution.exact_matcher import process_exact_matches
from src.resolution.candidate_generator import find_top_candidates
from src.resolution.pre_processor import should_reject, create_rejection_decision
from src.resolution.audit_logger import save_pipeline_audit
# from src.resolution.llm_resolver import resolve_candidates # Uncomment when ready for AI

def run_test():
    # ---------------------------------------------------------
    # NEW PATH DEFINITIONS
    # ---------------------------------------------------------
    test_file_path = "data/input/MSC ORNELLA UF621A TINCAN.pdf CAL ADDI.xlsx"
    master_excel_path = "data/input/master_accounts.xlsx"
    master_json_path = "data/reference/master_list_json.json"  # <-- Updated to save in reference
    
    os.makedirs("data/output", exist_ok=True)
    os.makedirs("data/input", exist_ok=True)
    os.makedirs("data/reference", exist_ok=True)  # <-- Ensure reference folder exists
    
    # ---------------------------------------------------------
    # STEP 0: CONVERT MASTER EXCEL TO JSON
    # ---------------------------------------------------------
    print("🔄 Preparing Master List...")
    ingest_master_list_excel(master_excel_path, master_json_path)
    
    # ---------------------------------------------------------
    # OUTPUT 1: The Raw Excel Data JSON
    # ---------------------------------------------------------
    raw_container_records = parse_shipping_file(test_file_path)
    with open("data/output/1_raw_excel_data.json", "w") as f:
        json.dump([json.loads(r.model_dump_json()) for r in raw_container_records], f, indent=2)

    # ---------------------------------------------------------
    # OUTPUT 2: The Unique BL Level Records
    # ---------------------------------------------------------
    unique_bls = {r.bill_of_lading: r for r in raw_container_records if r.bill_of_lading}.values()
    bl_level_records = list(unique_bls)
    with open("data/output/2_unique_bl_records.json", "w") as f:
        json.dump([json.loads(r.model_dump_json()) for r in bl_level_records], f, indent=2)
            
    # ---------------------------------------------------------
    # EXACT MATCH & PRE-FILTER STAGES
    # ---------------------------------------------------------
    # Notice we are now using the newly generated master_json_path!
    exact_matches, unmatched_records = process_exact_matches(bl_level_records, master_json_path)
    
    to_vector_search = []
    auto_rejected = []
    for record in unmatched_records:
        if should_reject(record.messy_party_name):
            auto_rejected.append(create_rejection_decision(record.messy_party_name))
        else:
            to_vector_search.append(record)
            
    # ---------------------------------------------------------
    # OUTPUT 3 & 4: Vector Search Math & Passed Candidates
    # ---------------------------------------------------------
    candidates, math_debug_log = find_top_candidates(to_vector_search, master_json_path)
    
    # Print Gatekeeper Stats
    passed_count = sum(1 for item in math_debug_log if item["passed_gatekeeper"] is True)
    failed_count = sum(1 for item in math_debug_log if item["passed_gatekeeper"] is False)
    
    print("\n" + "="*50)
    print("📊 VECTOR SEARCH GATEKEEPER RESULTS")
    print("="*50)
    print(f"✅ passed_gatekeeper: true  -> {passed_count} records")
    print(f"❌ passed_gatekeeper: false -> {failed_count} records")
    print("="*50 + "\n")

    with open("data/output/3_vector_math_debug.json", "w") as f:
        json.dump(math_debug_log, f, indent=2)
        
    with open("data/output/4_vector_passed_candidates.json", "w") as f:
        json.dump([json.loads(c.model_dump_json()) for c in candidates], f, indent=2)
    
    # ---------------------------------------------------------
    # OUTPUT 5: Final Decisions (LLM Skipped for now)
    # ---------------------------------------------------------
    llm_decisions = [] 
    
    final_decisions = exact_matches + auto_rejected + llm_decisions
    with open("data/output/5_final_decisions.json", "w") as f:
        json.dump([json.loads(d.model_dump_json()) for d in final_decisions], f, indent=2)
    
    # ---------------------------------------------------------
    # AUDIT TRAIL
    # ---------------------------------------------------------
    save_pipeline_audit(len(bl_level_records), len(exact_matches), len(auto_rejected), len(to_vector_search), len(candidates))
            
    print(f"\n✅ Diagnostic run complete! Files generated in data/output/")

if __name__ == "__main__":
    run_test()