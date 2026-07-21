# `src/core/` — Data Models & Configuration

This module contains the foundational building blocks used across the entire pipeline.

## Files

### `models.py` — Pydantic Data Schemas

Defines the strict data contracts that every module must follow:

| Model | Purpose |
|-------|---------|
| `ShippingRecord` | Universal schema that every parser outputs. Contains: `shipping_line`, `vessel_name`, `container_number`, `bill_of_lading`, `messy_party_name`, `party_role`, `port_of_discharge`, `eta` |
| `ResolutionCandidate` | A messy name + its top candidate master accounts (sent to vector search / LLM) |
| `LLMMatchDecision` | The structured output from the matching pipeline — `matched`, `resolved_master_name`, `confidence_score`, `reasoning` |
| `AccountShipmentSummary` | Groups multiple containers under one resolved master account for reporting |

### `config.py` — Configuration Loader

- Reads `config.yaml` from the project root at import time
- Exposes a global `config` dictionary used by all modules
- Usage: `from src.core.config import config`

> **Note:** Because config is loaded at import time, you must restart the Streamlit app (not just rerun) if you change `config.yaml`.

## Key Design Decisions

- **Pydantic models enforce strict typing** — parsers can't output malformed data
- **Optional fields** (`vessel_name`, `eta`, etc.) allow parsers to omit data they don't have without breaking the schema
- **Single config source** — all thresholds, paths, and business rules live in `config.yaml`, not scattered across code
