
# Container Arrival List (CAL) Resolution Pipeline

An automated data extraction and entity resolution pipeline that processes unstructured shipping documents (Container Arrival Lists) and matches incoming freight consignees to a master accounts database.

## What It Does

Shipping lines (MSC, Hapag-Lloyd, ONE, COSCO) each send container arrival lists in different messy Excel formats. This pipeline:

1. **Ingests** any supported Excel file and extracts structured data
2. **Matches** messy consignee names to your master accounts list
3. **Surfaces** ambiguous records for AI-assisted resolution
4. **Reports** results via a Streamlit dashboard with download support

## Architecture

```
Excel Upload ──► Router ──► Line-Specific Parser ──► Universal Schema
                                                          │
                            ┌─────────────────────────────┘
                            ▼
                     Exact Matcher (Pass 1: Normalized, Pass 2: Core Brand)
                            │
                     ┌──────┴──────┐
                     ▼             ▼
               ✅ Matched    Unmatched
                                   │
                            Junk Pre-Filter
                            │             │
                            ▼             ▼
                     🔴 Rejected    Vector Search (FAISS + Sentence Transformers)
                                          │
                                   ┌──────┴──────┐
                                   ▼             ▼
                            Below Threshold   🟡 Top Candidates ──► LLM Resolver (Ollama)
                            (Dropped)                                      │
                                                                    Final Decisions
```

## Quick Start

```bash
# 1. Clone and enter the project
git clone https://github.com/opeyemiloc/RE-cal-resolution-pipeline.git
cd RE-cal-resolution-pipeline

# 2. Create and activate a virtual environment
python -m venv re_env
source re_env/Scripts/activate  # Git Bash on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the Streamlit app
streamlit run app.py
```

The app opens at `http://localhost:8501`. Upload a **Master Accounts Excel** and a **Manifest Excel** from the sidebar, then click **Run Pipeline**.

## Directory Structure

```
├── app.py                  # Streamlit GUI entry point
├── config.yaml             # All pipeline settings (paths, thresholds, routing keywords)
├── requirements.txt        # Python dependencies
│
├── data/
│   ├── input/              # Uploaded Excel files land here
│   ├── output/             # Pipeline results and audit logs
│   └── reference/          # Generated master list JSON, match history
│
├── src/
│   ├── core/               # Data models (Pydantic) and config loader
│   ├── ingestion/          # Router + shipping line parsers (MSC, Hapag, ONE, COSCO)
│   │   └── parsers/        # One parser per carrier + master list parser
│   ├── resolution/         # Matching pipeline (exact → junk filter → vector → LLM)
│   └── reporting/          # Email generator (WIP)
│
└── templates/              # HTML/Jinja templates for reports (WIP)
```

> See the `README.md` inside each subfolder for detailed documentation on that module.

## Supported Shipping Lines

| Carrier      | File Keywords               | Parser     | Format Notes                        |
|--------------|-----------------------------|------------|-------------------------------------|
| MSC          | `msc`                       | `msc.py`   | 5 metadata rows, clean headers      |
| Hapag-Lloyd  | `hapag`, `hlc`, `vancouver star` | `hapag.py` | 7 metadata rows, leading empty col  |
| ONE          | `navios`, `o.n.e`, `one nig`    | `one.py`   | 8 metadata rows, split header rows  |
| COSCO        | `cosco`, `kota lagu`, `coscocal` | `cosco.py` | No metadata, headers on row 0       |

To add a new carrier, see [`src/ingestion/README.md`](src/ingestion/README.md).

## Configuration

All tunable settings live in [`config.yaml`](config.yaml):

- **`paths`** — Input/output/reference directories
- **`thresholds`** — Vector search quality gate, minimum name length
- **`llm`** — Model name and temperature for Ollama
- **`business_logic`** — Suffix words, junk patterns, bank keywords
- **`routing`** — Filename keywords that map to each parser

## Tech Stack

- **Python 3.x** with Pydantic for data validation
- **pandas** for Excel parsing
- **FAISS + Sentence Transformers** for vector similarity search
- **Ollama (Llama 3.2)** for LLM-based entity resolution
- **Streamlit** for the web GUI
- **PyYAML** for configuration
