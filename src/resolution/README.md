# `src/resolution/` — Entity Matching Pipeline

This module takes the cleaned `ShippingRecord` list from ingestion and resolves each messy consignee name against the master accounts database. It uses a multi-stage funnel that gets progressively more expensive.

## Pipeline Stages

```
Unique BL Records
       │
       ▼
┌─────────────────┐
│  Exact Matcher   │  Pass 1: Normalized string match
│                  │  Pass 2: Core brand match (trailing suffixes stripped)
└──────┬──────────┘
       │
  Unmatched records
       │
       ▼
┌─────────────────┐
│   Pre-Processor  │  Rejects junk names (TO ORDER, NULL, too short)
│   (Junk Filter)  │
└──────┬──────────┘
       │
  Valid unmatched records
       │
       ▼
┌─────────────────────┐
│  Candidate Generator │  FAISS vector search with Sentence Transformers
│  (Vector Search)     │  Returns top 3 candidates if best distance ≤ threshold
└──────┬──────────────┘
       │
  Top candidates
       │
       ▼
┌─────────────────┐
│   LLM Resolver   │  Ollama (Llama 3.2) evaluates candidates
│                  │  Returns structured match decision
└──────────────────┘
```

## Files

### `normalizer.py` — Name Cleaning

Standardizes messy names for accurate comparison:
- Uppercases everything
- Removes punctuation (`.`, `,`, `-`)
- Expands abbreviations: `LTD` → `LIMITED`, `NIG` → `NIGERIA`, `CO` → `COMPANY`, `INTL` → `INTERNATIONAL`, `IND` → `INDUSTRIES`
- Collapses multiple spaces

### `exact_matcher.py` — Deterministic Matching

Two-pass exact matching (no AI needed):

- **Pass 1 (Normalized):** Direct string comparison after normalization. Confidence: 100%.
- **Pass 2 (Core Brand):** Strips trailing corporate suffixes (LIMITED, PLC, ENTERPRISES, etc.) and compares core brand names. Includes an **ambiguity guard** — if two master accounts share the same core brand (e.g., "ABC LTD" and "ABC PLC"), it skips rather than guessing wrong.

Suffix words are loaded from `config.yaml` → `business_logic.suffix_words`.

### `pre_processor.py` — Junk Filter

Auto-rejects names that are clearly not real companies:
- Names shorter than `min_name_length` (default: 4 characters)
- Names containing junk patterns: `TO ORDER`, `NULL`, `UNKNOWN`, `BANK`, etc.

### `candidate_generator.py` — Vector Search

For records that survive the junk filter:
1. Encodes all master account names using `all-MiniLM-L6-v2` (Sentence Transformers)
2. Builds a FAISS index for fast similarity search
3. For each messy name, finds the top 3 nearest master accounts
4. Applies a **quality gate** — only passes records where `best_distance ≤ vector_quality_threshold` (default: 0.5)
5. Returns a debug log with distances for diagnostics

### `llm_resolver.py` — AI Resolution

For the hardest cases that pass vector search:
1. Sends the cleaned messy name + top 3 candidates to Ollama (Llama 3.2)
2. Uses a structured system prompt with matching rules
3. Forces the LLM to output a `LLMMatchDecision` (Pydantic schema)
4. Returns `matched`, `resolved_master_name`, `confidence_score`, and `reasoning`

> **Status:** LLM resolution is built but currently skipped in the Streamlit app pipeline. Candidates are displayed in the "Waiting for AI" queue.

### `audit_logger.py` — Pipeline Metrics

Saves a timestamped audit trail to `data/output/pipeline_audit.json` after each run:
- Total BLs processed
- Fast-path (exact) matches
- Pre-filter rejections
- Records sent to vector search
- Records sent to LLM

## Configuration

All thresholds and patterns are in `config.yaml`:

| Setting | Location | Default |
|---------|----------|---------|
| Vector quality threshold | `thresholds.vector_quality_threshold` | `0.5` |
| Min name length | `thresholds.min_name_length` | `4` |
| LLM model | `llm.model_name` | `llama3.2:3b` |
| LLM temperature | `llm.temperature` | `0` |
| Suffix words | `business_logic.suffix_words` | 17 entries |
| Junk patterns | `business_logic.junk_patterns` | 7 entries |
| Bank keywords | `business_logic.bank_keywords` | 5 entries |
