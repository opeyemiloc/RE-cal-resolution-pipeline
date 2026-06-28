
# Container Arrival List (CAL) Resolution Pipeline

An automated data extraction and entity resolution pipeline designed to process unstructured shipping documents (Container Arrival Lists) and match incoming freight to assigned master accounts.

## Architecture

This project utilizes a modular, Two-Stage Entity Resolution architecture to handle messy, human-entered logistics data:

1. **Adapter Pattern (Ingestion):** A dynamic router inspects incoming Excel files and sends them to shipping-line-specific parsers (e.g., MSC, ZIM). These parsers extract core data points (Container Number, Consignee, Notify Party) and map them to a Universal Internal Schema.
2. **Pre-Filtering (Resolution Stage 1):** Fast text/vector matching filters a master list of accounts down to the top 5 most likely candidates for each messy record.
3. **LLM Reasoning (Resolution Stage 2):** An AI model evaluates the small candidate pool against the target string to resolve typos, abbreviations, and address leaks with high accuracy.
4. **Automated Reporting:** The resolved structured data is injected into an HTML template to generate clean, readable insights for sales and relationship teams.

## Directory Structure

- `data/` - Houses raw input sheets, reference databases, and generated outputs. *(Ignored by Git)*
- `src/core/` - Global configurations and strict Pydantic data schemas.
- `src/ingestion/` - The Router and line-specific Excel parsers (MSC, etc.).
- `src/resolution/` - The candidate generator and AI reasoning engine.
- `src/reporting/` - Email and insight templating.
- `templates/` - HTML/Jinja templates for final output.
