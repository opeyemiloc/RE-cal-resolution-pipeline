# 🔍 Code Review Report — CAL Resolution Pipeline

**Date:** 2026-07-22  
**Branch:** `docs/project-readme-updates`  
**Reviewed:** All source files across ingestion, resolution, core, app, and config

---

## Summary

The pipeline architecture is solid — modular parsers, config-driven routing, and a multi-stage resolution funnel. However, the review uncovered **8 critical bugs** that will cause incorrect results or crashes, plus several important improvements for code quality and performance.

| Severity | Count |
|----------|-------|
| 🔴 Critical (bugs, wrong results, crashes) | 8 |
| 🟡 Important (performance, maintainability) | 8 |
| 🟢 Nice-to-have (polish, best practices) | 5 |

---

## 🔴 Critical Issues

### 1. Pre-processor falsely rejects legitimate companies
**File:** [pre_processor.py](file:///C:/Users/User/Desktop/notify_tool/src/resolution/pre_processor.py)  
**Line:** 13 — `any(p in n for p in junk_patterns)`

Uses **substring matching**, not word matching. This means:
- `"BANK"` in junk_patterns rejects `"ACCESS BANK PLC"`, `"FIRST BANK OF NIGERIA"`, `"WEMA BANK"`
- `"LOC"` rejects anything containing those letters: `"INTERLOCK NIGERIA"`, `"ALLOCATED TRADING"`
- `"SAME AS"` could reject `"SAME ASSET HOLDINGS"`

**Impact:** Real customers are silently dropped from the pipeline with zero matches.

**Fix:** Use word-boundary matching or exact token comparison instead of `in`.

---

### 2. `"BANK"` stripping in salvage logic corrupts company names
**Files:** All 4 parsers ([msc.py](file:///C:/Users/User/Desktop/notify_tool/src/ingestion/parsers/msc.py), [hapag.py](file:///C:/Users/User/Desktop/notify_tool/src/ingestion/parsers/hapag.py), [one.py](file:///C:/Users/User/Desktop/notify_tool/src/ingestion/parsers/one.py), [cosco.py](file:///C:/Users/User/Desktop/notify_tool/src/ingestion/parsers/cosco.py))

The salvage logic does `.replace("BANK", "")`, which corrupts names:
- `"ACCESS BANK PLC"` → `"ACCESS  PLC"`
- `"EMBANKMENT LOGISTICS"` → `"EMMENT LOGISTICS"`

**Fix:** Use regex word boundaries: `re.sub(r'\bBANK\b', '', name)`.

---

### 3. Streamlit results vanish on any interaction
**File:** [app.py](file:///C:/Users/User/Desktop/notify_tool/app.py)

All pipeline results live inside `if run_btn:` — a Streamlit ephemeral trigger. The moment a user clicks the download button or interacts with the page, Streamlit reruns the script, `run_btn` becomes `False`, and **all metrics, tables, and download buttons disappear**.

**Fix:** Store results in `st.session_state` and render them outside the button block.

---

### 4. SentenceTransformer model reloads on every pipeline run
**File:** [candidate_generator.py](file:///C:/Users/User/Desktop/notify_tool/src/resolution/candidate_generator.py#L12)  
**Line:** 12 — `model = SentenceTransformer('all-MiniLM-L6-v2')`

Loads a ~90MB neural network into memory on **every single function call**. This causes:
- Multi-second delays per run
- Potential OOM on memory-constrained systems
- Completely unnecessary since the model never changes

**Fix:** Load once at module level, or use `@st.cache_resource` in the Streamlit context.

---

### 5. Routing keyword `"ONE"` is uppercase — will never match
**File:** [config.yaml](file:///C:/Users/User/Desktop/notify_tool/config.yaml) — routing.one

The router lowercases filenames before matching (`filename.lower()`), but config contains `"ONE"` in uppercase. `"ONE" in "tincan navios destiny v.090w -one.xlsx"` → **always `False`**.

**Fix:** Lowercase all routing keywords in config, or lowercase them in the router.

---

### 6. `.gitignore` has broken syntax — section headers treated as file patterns
**File:** [.gitignore](file:///C:/Users/User/Desktop/notify_tool/.gitignore)

Section headers like `=========================`, `1. Python Environment`, `Ignore all files in the input...` are **missing `#` prefixes**. Git interprets every word as a pattern to ignore.

Also: `pycache/` should be `__pycache__/`, and `re_env/` is not listed.

---

### 7. Unclosed file handle + missing encoding in candidate generator
**File:** [candidate_generator.py](file:///C:/Users/User/Desktop/notify_tool/src/resolution/candidate_generator.py#L13)  
**Line:** 13 — `json.load(open(master_accounts_path, 'r'))`

- File opened without `with` statement — handle never closed
- Missing `encoding='utf-8'` — will crash on Windows if JSON contains special characters

---

### 8. Suffix words `"LTD."` in config will never match after normalization
**File:** [config.yaml](file:///C:/Users/User/Desktop/notify_tool/config.yaml) — suffix_words

The normalizer strips all periods (`.replace(".", "")`), so by the time `strip_trailing_suffixes()` runs, `"LTD."` has already become `"LTD"`. The `"LTD."` entry in suffix_words is dead code.

---

## 🟡 Important Improvements

### 9. Massive code duplication across parsers
**Files:** All 4 carrier parsers

The salvage logic (bank detection → notify party fallback → junk stripping → UNKNOWN fallback) is **copy-pasted identically** across MSC, Hapag, ONE, and COSCO parsers (~30 lines each = ~120 lines of duplication).

**Fix:** Extract to a shared function in `src/ingestion/parsers/common.py`.

---

### 10. MSC parser lacks expected column safety check
**File:** [msc.py](file:///C:/Users/User/Desktop/notify_tool/src/ingestion/parsers/msc.py)

Hapag, ONE, and COSCO all have strict `expected_columns` checks that fail loudly. MSC silently proceeds with `row.get()` defaults, producing garbage data if column names change.

---

### 11. ONE parser may truncate container numbers
**File:** [one.py](file:///C:/Users/User/Desktop/notify_tool/src/ingestion/parsers/one.py)

ONE files split container IDs across two columns (`Cont. Prefix` + separate number column). The parser only reads `Cont. Prefix`, potentially losing the numeric portion.

---

### 12. Normalizer missing common abbreviations
**File:** [normalizer.py](file:///C:/Users/User/Desktop/notify_tool/src/resolution/normalizer.py)

Only handles 5 abbreviations. Missing: `CORP`→`CORPORATION`, `ENT`→`ENTERPRISES`, `MFG`→`MANUFACTURING`, `DIST`→`DISTRIBUTORS`, `GRP`→`GROUP`, `TECH`→`TECHNOLOGY`, `BROS`→`BROTHERS`.

Also: `\bCO\b` expands `CO` to `COMPANY`, but `C/O` (care of) becomes `C O` after punctuation removal → `C COMPANY`.

---

### 13. Vector search encodes one name at a time (slow loop)
**File:** [candidate_generator.py](file:///C:/Users/User/Desktop/notify_tool/src/resolution/candidate_generator.py#L28-L29)

`model.encode([clean_messy])` is called inside a for-loop. All messy names should be batch-encoded in one call for much better performance.

---

### 14. `test_ingestion.py` has broken file paths
**File:** [test_ingestion.py](file:///C:/Users/User/Desktop/notify_tool/test_ingestion.py)

- References `"MSC ORNELLA UF621A TINCAN.pdf CAL ADDI.xlsx"` — actual file is `"...ADDI (1).xlsx"`
- Will crash with `FileNotFoundError` if run

---

### 15. `requirements.txt` has duplicates
**File:** [requirements.txt](file:///C:/Users/User/Desktop/notify_tool/requirements.txt)

Contains both pinned versions (`streamlit==1.58.0`) AND unpinned duplicates (`streamlit`) at the bottom. Also includes unnecessary transitive deps like `GitPython`, `sympy`, `uvicorn`.

---

### 16. Unused variables in parsers
**Files:** [one.py](file:///C:/Users/User/Desktop/notify_tool/src/ingestion/parsers/one.py) (line 65), [cosco.py](file:///C:/Users/User/Desktop/notify_tool/src/ingestion/parsers/cosco.py) (line 51)

Both extract `pol` (Port of Loading) but never pass it to `ShippingRecord`.

---

## 🟢 Nice-to-Have

### 17. Hapag docstring says `skiprows=4` but code uses `skiprows=7`
Minor documentation mismatch.

### 18. Config should include vector search `k` value and embedding model name
Currently hardcoded in `candidate_generator.py`.

### 19. `config.yaml` has typo `"VENTRURES"` (should be `"VENTURES"`)
Duplicate of correctly spelled entry — harmless but messy.

### 20. `party_role` values exceed schema definition
Schema says "Either 'Consignee' or 'Notify Party'" but parsers also produce `"Salvaged Consignee"` and `"Unknown"`. Should update the schema description.

### 21. No `encoding='utf-8'` on file reads/writes across resolution modules
[exact_matcher.py](file:///C:/Users/User/Desktop/notify_tool/src/resolution/exact_matcher.py), [audit_logger.py](file:///C:/Users/User/Desktop/notify_tool/src/resolution/audit_logger.py) — could crash on Windows with special characters.

---

## Recommended Fix Priority

| Order | Issue # | What | Why First |
|-------|---------|------|-----------|
| 1 | #1, #2 | Fix BANK/LOC false rejections | Real customers being silently dropped |
| 2 | #3 | Add `st.session_state` to app.py | Results vanishing is a UX blocker |
| 3 | #4, #7, #13 | Fix candidate_generator.py | Performance + resource leak |
| 4 | #9 | Extract shared salvage logic | Eliminate 120 lines of duplication |
| 5 | #5, #6 | Fix config.yaml + .gitignore | Routing broken + git tracking broken |
| 6 | #8, #12 | Clean up suffix words + normalizer | Dead config entries + missed matches |
| 7 | #10, #11 | Harden MSC + ONE parsers | Data quality |
| 8 | #14, #15, #16 | Housekeeping | Test script + deps + unused vars |
