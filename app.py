import streamlit as st
import os
import json
from src.ingestion.router import parse_shipping_file
from src.ingestion.parsers.master_parser import ingest_master_list_excel
from src.resolution.exact_matcher import process_exact_matches
from src.resolution.candidate_generator import find_top_candidates
from src.resolution.pre_processor import should_reject, create_rejection_decision
from src.resolution.llm_resolver import resolve_candidates
from src.core.config import config

# --- PAGE SETUP ---
st.set_page_config(page_title="Logistics AI Matcher", page_icon="🚢", layout="wide")

st.title("🚢 AI Logistics Name Matcher")
st.markdown("""
Upload a **Master Accounts List** and a **Shipping Manifest (e.g., MSC, Hapag-Lloyd)**. 
The system will automatically extract, clean, route, and match the consignee names!
""")

# --- SIDEBAR: FILE UPLOADS ---
with st.sidebar:
    st.header("1. Upload Data")
    master_file = st.file_uploader("Upload Master Accounts (Excel)", type=["xlsx"])
    manifest_file = st.file_uploader("Upload Shipping Manifest (Excel)", type=["xlsx"])
    run_btn = st.button("🚀 Run Pipeline", type="primary", use_container_width=True)

# --- PIPELINE EXECUTION ---
if run_btn:
    if not master_file or not manifest_file:
        st.warning("⚠️ Please upload both Excel files before running.")
    else:
        with st.spinner("Processing pipeline..."):
            try:
                # 1. Save uploaded files to the input directory temporarily
                os.makedirs(config['paths']['input_dir'], exist_ok=True)
                
                master_path = os.path.join(config['paths']['input_dir'], master_file.name)
                manifest_path = os.path.join(config['paths']['input_dir'], manifest_file.name)
                
                with open(master_path, "wb") as f:
                    f.write(master_file.getbuffer())
                with open(manifest_path, "wb") as f:
                    f.write(manifest_file.getbuffer())

                # 2. Run Master Parser
                master_json_path = config['paths']['master_json']
                ingest_master_list_excel(master_path, master_json_path)

                # 3. Parse Manifest & Extract Unique BLs
                raw_records = parse_shipping_file(manifest_path)
                unique_bls = {r.bill_of_lading: r for r in raw_records if r.bill_of_lading}.values()
                bl_level_records = list(unique_bls)

                # 4. Run Exact Matcher
                exact_matches, unmatched_records = process_exact_matches(bl_level_records, master_json_path)

                # 5. Run Pre-Processor (Junk Filter)
                to_vector_search = []
                auto_rejected = []
                for record in unmatched_records:
                    if should_reject(record.messy_party_name):
                        auto_rejected.append(create_rejection_decision(record.messy_party_name))
                    else:
                        to_vector_search.append(record)

                # 6. Run Vector Search
                candidates, _ = find_top_candidates(to_vector_search, master_json_path)

                # 7. Run LLM Resolution
                llm_decisions = []
                if candidates:
                    with st.spinner("🧠 Running AI Resolution on ambiguous records..."):
                        llm_decisions = resolve_candidates(candidates)

                # Combine Results
                final_decisions = exact_matches + auto_rejected + llm_decisions
                
                # Store results in session_state
                st.session_state.bl_level_records = bl_level_records
                st.session_state.exact_matches = exact_matches
                st.session_state.auto_rejected = auto_rejected
                st.session_state.candidates = candidates
                st.session_state.llm_decisions = llm_decisions
                st.session_state.final_decisions = final_decisions
                st.session_state.pipeline_ran = True
                
                st.success("✅ Pipeline Complete!")
            except Exception as e:
                st.error(f"Pipeline failed: {str(e)}")

# --- DISPLAY RESULTS ---
if st.session_state.get('pipeline_ran', False):
    st.header("📊 Pipeline Analytics")
    
    # Metrics Dashboard
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Unique BLs", len(st.session_state.bl_level_records))
    col2.metric("🟢 Exact Matches", len(st.session_state.exact_matches))
    col3.metric("🔴 Auto-Rejected (Junk)", len(st.session_state.auto_rejected))
    col4.metric("🟡 Sent to AI Queue", len(st.session_state.candidates), help="Ambiguous names requiring Vector Search/LLM.")

    st.divider()

    # 1. Final
    st.subheader("Final Decisions")
    final_json = [json.loads(d.model_dump_json()) for d in st.session_state.final_decisions]
    if final_json:
        st.dataframe(final_json, use_container_width=True)
        
        # Download Button
        json_str = json.dumps(final_json, indent=2)
        st.download_button(
            label="📥 Download JSON Results",
            data=json_str,
            file_name="pipeline_results.json",
            mime="application/json",
            type="primary"
        )
    else:
        st.info("No decisions available.")

    # 2. Deterministic
    st.subheader("Deterministic Decisions")
    deterministic = st.session_state.exact_matches + st.session_state.auto_rejected
    if deterministic:
        det_json = [json.loads(d.model_dump_json()) for d in deterministic]
        st.dataframe(det_json, use_container_width=True)
    else:
        st.info("No deterministic decisions available.")
    
    # 3. Ambiguous
    st.subheader("Ambiguous Records")
    if st.session_state.candidates:
        candidates_json = [json.loads(c.model_dump_json()) for c in st.session_state.candidates]
        st.dataframe(candidates_json, use_container_width=True)
    else:
        st.info("No ambiguous records.")
        
    # 4. AI Result
    st.subheader("AI Results")
    if st.session_state.get('llm_decisions'):
        llm_json = [json.loads(d.model_dump_json()) for d in st.session_state.llm_decisions]
        st.dataframe(llm_json, use_container_width=True)
    else:
        st.info("No AI results available.")