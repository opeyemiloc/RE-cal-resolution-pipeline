# `src/ingestion/` — File Routing & Excel Parsing

This module is responsible for taking raw, messy Excel files from different shipping lines and converting them into a clean, universal format (`ShippingRecord`).

## How It Works

```
Uploaded Excel ──► router.py (inspects filename) ──► correct parser ──► List[ShippingRecord]
```

### `router.py` — The Gatekeeper

1. Takes a file path
2. Lowercases the filename
3. Checks it against keyword lists defined in `config.yaml` under `routing:`
4. Dispatches to the matching parser function via `PARSER_REGISTRY`

The registry maps config keys to parser functions:

```python
PARSER_REGISTRY = {
    "one":   ("ONE",         parse_one_excel),
    "cosco": ("COSCO",       parse_cosco_excel),
    "hapag": ("HAPAG-LLOYD", parse_hapag_excel),
    "msc":   ("MSC",         parse_msc_excel),
}
```

### `parsers/` — Line-Specific Parsers

Each shipping line sends Excel files in a different format. Each parser handles the quirks of its carrier:

| Parser | `skiprows` | Key Columns | Notes |
|--------|-----------|-------------|-------|
| `msc.py` | 5 | `Bill of Lading Number`, `Container Number`, `Consignee Name`, `Notify1 Name` | Also extracts `Port of Discharge` and `ETA` |
| `hapag.py` | 7 | `B/L NO`, `CONTAINER NO`, `CONSIGNEE`, `NOTIFY PARTY` | Drops leading empty column |
| `one.py` | 8 | `B/L NO`, `Cont. Prefix`, `Receiver`, `Notify Name` | Has split headers across 2 rows — drops the sub-header row |
| `cosco.py` | 0 | `BL Number`, `Container ID`, `Consignee Name`, `NOTIFY` | Cleanest format, no metadata to skip |

### `parsers/master_parser.py` — Master Accounts Converter

Converts the Master Accounts Excel file into a flat JSON array of company names. It auto-detects the name column by looking for keywords like `name`, `account`, `company`, or `customer` in the header.

## Salvage Logic (Shared Across All Parsers)

Every parser includes the same consignee recovery logic:

1. If Consignee is **empty, a bank name, or junk** (e.g., "TO ORDER"):
   - **Try Notify Party** — use it if it's a real name (not "SAME AS CONSIGNEE")
   - **Strip junk prefixes** — e.g., "TO THE ORDER OF JUDE EKELEDO" → "JUDE EKELEDO"
   - **Last resort** — mark as "UNKNOWN"

Bank keywords and junk patterns are loaded from `config.yaml`.

## How to Add a New Shipping Line

1. **Create the parser** — Add `src/ingestion/parsers/<carrier>.py` with a function `parse_<carrier>_excel(file_path) -> List[ShippingRecord]`
2. **Register it** — Add an entry to `PARSER_REGISTRY` in `router.py`
3. **Add routing keywords** — Add filename keywords under `routing:` in `config.yaml`

That's it — no other files need to change.
