# PLAN.md

## Project
PHCC / Integra Fee Schedule Comparison Pipeline

## Goal
Create an auditable workflow that cleans uploaded fee schedule CSVs, flattens HCPCS ranges, normalizes modifiers, profiles note-based pricing, and produces a payer-by-payer comparison between Integra proposals and PHCC current schedules, with CMS/OHA public benchmark checks where applicable.

---

## Workspace Layout (current)

```
PHCC/
  analyze_fee_schedules.py     # v2 main comparison pipeline (1,047 lines)
  clean_phcc_files.py          # PHCC source cleaner (434 lines)
  check_clean_output.py        # Validation diagnostic
  scripts/                     # Backup copies of scripts
  data/
    Contract/                  # PHCC current rate CSVs (canonical source)
      PHCC_OR_CONTRACTED.csv
      PHCC_OR_PARTICIPATING.csv
      PHCC_WA_PARTICIPATING.csv
    cms/                       # Public benchmarks + HCPCS reference
      2026_CMS_HCPCS.csv
      CMS_2026_Q1_OR.csv
      CMS_2026_Q1_WA.csv
      OHA_FFS_09_2025_RAW.csv
    INTEGRA_PHP_FFS/           # Integra proposed carveouts
      Integra_PHP_CARVEOUTS_COMMERCIAL.csv
      Integra_PHP_CARVEOUTS_ASO.csv
      Integra_PHP_CARVEOUTS_MEDICARE.csv
      INTEGRA_PHP_CARVEOUTS_MEDICAID.csv
    cleaned/                   # Output from clean_phcc_files.py
      PHCC_OR_CONTRACTED_CLEAN.csv
      PHCC_OR_PARTICIPATING_CLEAN.csv
      PHCC_WA_PARTICIPATING_CLEAN.csv
      PHCC_hcpcs_audit.csv
      PHCC_hcpcs_range_expansion_audit.csv
      PHCC_K0_artifact_review.csv
  output/                      # Output from analyze_fee_schedules.py (empty)
```

---

## What Is Already Known From The Uploaded Files

### File coverage
Present now:
- Integra commercial / ASO / Medicare / Medicaid CSVs (1,079 rows each)
- PHCC OR contracted / OR participating / WA participating CSVs (in `data/Contract/`)
- CMS WA and OR Q1 2026 CSVs (in `data/cms/`)
- OHA Medicaid CSV (in `data/cms/`)
- CMS 2026 HCPCS reference (8,624 codes, in `data/cms/`)

### Confirmed source issues (resolved)
- ~~PHCC contains OCR-style HCPCS corruption~~ → Contract files are clean (0 OCR issues)
- PHCC contains range rows → 105 codes expanded from ranges, 3 category ranges kept as-is
- PHCC contains mixed modifier formats → NU/RR flattened to separate rows
- PHCC contains non-numeric pricing notes → classified into 8+ note types, not coerced

### Source data fixes applied
- `E2291-E1239` → `E2291-E2295` in PHCC_OR_CONTRACTED.csv (reversed range typo, verified via CMS HCPCS + AAPC)

### Cleaned output stats
- 1,059 total cleaned rows (330 OR_CONTRACTED + 199 OR_PARTICIPATING + 530 WA_PARTICIPATING)
- 99.7% valid HCPCS (1,056 of 1,059)
- 3 remaining audit items: all CATEGORY_RANGE (intentional L-code catch-alls)

---

## PHASE 1 — Intake and column detection
### Status: ✅ COMPLETE

### Objective
Standardize each file into a known schema without losing raw source columns.

### Implementation
- `clean_phcc_files.py`: `process_file()` detects columns by name, preserves originals as `orig_*` prefix
- `analyze_fee_schedules.py`: dedicated `load_*()` functions per file type
- Source traceability: `source_file` + `source_row` columns in all outputs

---

## PHASE 2 — PHCC HCPCS audit and deterministic cleanup
### Status: ✅ COMPLETE

### Objective
Validate PHCC HCPCS values before any comparison logic is attempted.

### Implementation
- `clean_phcc_files.py`: OCR correction table (38 K-code mappings), generic O→0 fallback, trailing-dash removal, multiline extraction, junk-char removal, embedded-junk regex
- Validation: `^[A-Z][0-9]{4}$` regex
- Issue classification: OCR_CORRECTED, TRAILING_DASH_REMOVED, JUNK_CHARS_REMOVED, MULTILINE_CLEANED, RANGE_EXPANDED, CATEGORY_RANGE, MALFORMED_RANGE, INVALID

### Outputs
- `PHCC_hcpcs_audit.csv`: 3 issues (all CATEGORY_RANGE)
- `PHCC_K0_artifact_review.csv`: 38 corrections with confidence levels and blank `manual_verified` column

---

## PHASE 3 — HCPCS range expansion
### Status: ✅ COMPLETE (with intentional category-range policy)

### Objective
Convert one-to-many HCPCS range rows into atomic comparison rows.

### Implementation
- Small/medium ranges (≤100 codes): expanded deterministically → 105 individual codes
- Category ranges (>100 codes): classified as CATEGORY_RANGE, kept as single row
  - `L0112-L2861` (Orthotics, ~2,750 codes)
  - `L3000-L4631` (Orthotic procedures, ~1,632 codes)
  - `L8300-L8485` (Trusses/prosthetic socks, ~186 codes)
- Reversed ranges detected and rejected (E2291-E1239 was fixed in source)

### Output
- `PHCC_hcpcs_range_expansion_audit.csv`: 105 expanded rows with source traceability

### Open decision
Category ranges require business policy: expand vs keep as catch-all pricing rules.

---

## PHASE 4 — Modifier normalization and row explosion
### Status: ✅ COMPLETE

### Objective
Create a stable modifier key and a comparison-ready row set.

### Implementation
- `clean_phcc_files.py`: `flatten_modifier()` splits NU/RR → ["NU", "RR"], strips trailing `*`
- `analyze_fee_schedules.py`: 3-tier matching (exact → proposed-mod-blank → HCPCS-only)
- Row explosion: cartesian product of HCPCS codes × modifiers materialized in cleaned CSVs
- `modifier_original` and `modifier_normalised` columns preserved

---

## PHASE 5 — Rate normalization
### Status: ✅ COMPLETE

### Objective
Separate numeric reimbursement from note-based pricing statements.

### Implementation
- `clean_phcc_files.py`: `classify_rate()` → numeric parse or note classification
- Note classes: PERCENT_OF_RETAIL, NON_BILLABLE, QUOTE_REQUIRED, PERCENT_OF_MEDICARE_ALLOWABLE, PREVAILING_STATE_RATES, PER_TIME_UNIT, COST_INVOICE, UNPARSED_TEXT
- Output columns per rate: `{col}_raw`, `{col}_numeric`, `{col}_note_type`, `{col}_note_detail`

---

## PHASE 6 — Comparison build
### Status: ⚠️ COMPLETE (needs integration fix)

### Objective
Join proposed rows to PHCC current rows using a defensible key.

### Implementation
- `analyze_fee_schedules.py`: `_process_one_proposed()` + `match_proposed_to_current()`
- Key: HCPCS_normalized + modifier, 3-tier fallback strategy
- States: OR, WA — Payers: Commercial, ASO, Medicare, Medicaid
- Comparison: HIGHER / LOWER / EQUAL / NOT_COMPARABLE / MISSING_CURRENT

### ⚠️ Critical integration gap
`analyze_fee_schedules.py` reads **raw Contract files** and reimplements cleanup inline.
It does NOT consume the cleaned CSVs from Phase 2.
Risk: logic divergence between `clean_phcc_files.py` and `analyze_fee_schedules.py`.

**Action required**: Refactor `analyze_fee_schedules.py` to load from `data/cleaned/` outputs.

---

## PHASE 7 — Benchmark checks
### Status: ✅ COMPLETE

### Objective
When proposed < current, compare against public benchmarks.

### Implementation
- Medicare: CMS_2026_Q1_OR.csv / CMS_2026_Q1_WA.csv
- Oregon Medicaid: OHA_FFS_09_2025_RAW.csv
- Washington Medicaid: explicitly flagged as MISSING_BENCHMARK
- Comparison: ABOVE_BENCHMARK / BELOW_BENCHMARK / EQUAL_TO_BENCHMARK / MISSING_BENCHMARK

---

## PHASE 8 — QA and exception review
### Status: ✅ COMPLETE

### Objective
Prevent silent bad joins or misleading comparisons.

### Implementation
- `review_required` boolean flag + `review_reason` concatenated text
- Triggers: invalid HCPCS, missing benchmark, fallback modifier match, note-only rate, duplicate keys
- Output: `fee_schedule_review_queue.csv`

---

## PHASE 9 — XLSX output enhancement (NEW)
### Status: 🔲 NOT STARTED

### Objective
Produce an executive-ready Excel workbook with formatting, conditional styling, and frozen panes.

### Tasks
1. Refactor `analyze_fee_schedules.py` to consume cleaned PHCC CSVs instead of raw files
2. Run end-to-end and validate output in `output/`
3. Enhance XLSX output with:
   - **Executive summary tab**: payer/state breakdown counts, % higher/lower/equal, average deltas
   - **Conditional formatting**: green for HIGHER, red for LOWER/BELOW_BENCHMARK, yellow for NOT_COMPARABLE/MISSING
   - **Frozen panes**: lock header row + HCPCS/modifier columns
   - **Column width auto-fit**: readable without manual resizing
   - **Number formatting**: currency for rate columns, percentage for delta columns
   - **Named ranges / filters**: auto-filter on all data tabs
   - **Review queue tab**: filtered view of flagged rows with color coding
   - **Benchmark comparison tab**: only rows where proposed < current, showing benchmark result
4. Add data validation annotations for note-based pricing columns
5. Add a "Data Sources" tab documenting file origins, row counts, and processing date

### XLSX tab structure (proposed)
| Tab | Content | Formatting |
|---|---|---|
| Executive Summary | Payer × state matrix, % higher/lower, avg delta | Conditional fill, bold headers |
| All Comparisons | Full master dataset | Frozen row 1 + cols A-C, auto-filter |
| Lower Than Current | Filtered: proposed < current | Red fill on delta |
| Below Benchmark | Filtered: below CMS/OHA floor | Red bold |
| Review Queue | Flagged rows | Yellow fill, review_reason column |
| Audit Trail | HCPCS audit + range expansion | Grouped by issue type |
| Data Sources | File inventory, row counts, date | Static reference |

### Done when
- XLSX opens in Excel with no manual formatting needed
- executive tab is decision-ready
- all tabs have frozen headers and auto-filters
- conditional formatting highlights action items

---

## Immediate Next Steps
1. ~~use the PHCC validator results to approve deterministic fixes~~ ✅
2. ~~define the exact `hcpcs_key + modifier_match_key + rate_side` join contract~~ ✅
3. ~~implement range expansion as a reusable function~~ ✅
4. ~~build PHCC row explosion for rate-side + modifier-side semantics~~ ✅
5. ~~normalize Integra/CMS/OHA modifiers to the same token model~~ ✅
6. ~~build the master comparison table~~ ✅
7. **Refactor analyze script to consume cleaned PHCC CSVs** ← current blocker
8. **Run end-to-end validation** → populate `output/`
9. **Enhance XLSX output** (Phase 9)
10. **Business review of category ranges** (L-code policy decision)

---

## Acceptance Criteria
The project is ready for business review only when:
- ~~PHCC HCPCS anomalies are fully audited~~ ✅
- ~~requested ranges are flattened~~ ✅
- ~~modifiers are normalized and mapped~~ ✅
- ~~note-based rate rows are preserved instead of guessed~~ ✅
- ~~lower-than-current benchmark checks are applied consistently~~ ✅
- ~~unresolved rows are isolated in a review queue~~ ✅
- analyze script consumes cleaned CSVs (not raw files)
- XLSX output is executive-ready with formatting and frozen panes
- end-to-end run completes with validated output in `output/`
