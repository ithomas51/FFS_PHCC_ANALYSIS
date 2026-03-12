# SKILL.md

## Skill Name
Fee Schedule Comparison Builder

## Purpose
Use this skill to normalize messy healthcare fee schedule extracts, repair deterministic OCR errors, flatten HCPCS ranges, map modifiers into comparison-ready keys, and build an auditable payer-by-payer rate comparison dataset.

This skill is designed for mixed-source fee schedule work where:
- some files come from OCR/PDF extraction
- PHCC/current rates and payer proposals must be compared
- Medicare/Medicaid public benchmarks are available for secondary checks
- source data contains ranges, OCR drift, and non-numeric reimbursement notes

---

## When To Use
Invoke this skill when the user asks for any of the following:

- compare proposed rates vs current rates
- normalize or audit fee schedule CSVs
- flatten HCPCS ranges
- repair OCR-corrupted HCPCS values
- map PHCC modifiers to Integra/CMS/OHA modifiers
- build review queues for pricing exceptions
- classify note-based pricing such as `Retail less 25%`
- enhance or reformat Excel comparison output

---

## Inputs Expected

### Proposed schedules (in `data/INTEGRA_PHP_FFS/`)
- `Integra_PHP_CARVEOUTS_COMMERCIAL.csv`
- `Integra_PHP_CARVEOUTS_ASO.csv`
- `Integra_PHP_CARVEOUTS_MEDICARE.csv`
- `INTEGRA_PHP_CARVEOUTS_MEDICAID.csv`

### Current schedules (in `data/Contract/`)
- `PHCC_OR_CONTRACTED.csv`
- `PHCC_OR_PARTICIPATING.csv`  (previously `PHCC_WA_PARTICIPATING.csv` mirrored here)
- `PHCC_WA_PARTICIPATING.csv`

### Public benchmarks (in `data/cms/`)
- `CMS_2026_Q1_OR.csv`
- `CMS_2026_Q1_WA.csv`
- `OHA_FFS_09_2025_RAW.csv`
- `2026_CMS_HCPCS.csv` (HCPCS description reference, 8,624 codes)

### Cleaned outputs (in `data/cleaned/`, produced by `clean_phcc_files.py`)
- `PHCC_OR_CONTRACTED_CLEAN.csv` (330 rows)
- `PHCC_OR_PARTICIPATING_CLEAN.csv` (199 rows)
- `PHCC_WA_PARTICIPATING_CLEAN.csv` (530 rows)
- `PHCC_hcpcs_audit.csv` (3 CATEGORY_RANGE items)
- `PHCC_hcpcs_range_expansion_audit.csv` (105 expanded rows)
- `PHCC_K0_artifact_review.csv` (38 OCR correction mappings)

---

## Output Contract

### Primary output
A comparison-ready master dataset with one row per comparison unit after expansion.

### Required supporting outputs
- HCPCS validation audit
- HCPCS range-expansion audit
- modifier mapping audit
- rate-note audit
- review queue
- summary metrics by payer/state
- Executive-ready XLSX workbook (multi-tab, formatted)

---

## Core Principles
1. Never silently repair ambiguous codes
2. Preserve raw values before cleaning
3. Separate deterministic cleanup from manual-review logic
4. Expand ranges before final matching
5. Normalize modifiers into tokens before comparison
6. Separate numeric rates from note-based rates
7. Keep an audit trail for every transformation
8. Consume cleaned PHCC data (not raw) for comparison builds

---

## Data Normalization Rules

### HCPCS single-code validity
Valid only if:

```regex
^[A-Z][0-9]{4}$
```

### Deterministic fixes allowed
- uppercase / trim
- whitespace removal
- trailing hyphen cleanup around a single code
- OCR `O` -> `0` in positions 2-5 when that yields a valid code
- leading valid HCPCS extraction when extra text follows the code

### Not auto-fixable
- question marks
- conflicting possible repairs
- malformed codes with no single deterministic interpretation

---

## HCPCS Range Handling
Normalize and expand values such as:
- `K0001-K0007`
- `A6530-A6541`
- `E2601 - E2610`

### Category ranges (policy: keep as single row)
Large umbrella ranges intentionally kept as-is and classified CATEGORY_RANGE:
- `L0112-L2861` (Orthotics catch-all)
- `L3000-L4631` (Orthotic procedures catch-all)
- `L8300-L8485` (Trusses/prosthetic socks catch-all)

Rules:
- small/medium ranges (≤100 codes): expand to one row per member code
- category ranges (>100 codes): keep as single row, classify CATEGORY_RANGE
- retain source row identity
- carry forward modifier / rate / description context
- record range start, range end, and member counts

---

## HCPCS Key Strategy

### Clean key
`hcpcs_key = cleaned single code`

### Expanded key
`hcpcs_key = expanded member code`

### Recommended composite comparison key
`state | payer_group | hcpcs_key | modifier_match_key | rate_side`

---

## Modifier Mapping Strategy

### Canonicalization
- uppercase
- strip `*`
- split on `/`, `,`, whitespace
- dedupe while preserving order

### Modifier patterns to support
- `NU`
- `RR`
- `TW`
- `NU/RR`
- `NU**/RR`
- `RR NU`
- `RR/QG`
- `RR/QE`
- `RR,QG,QF`

### Comparison behavior
- `NU` => purchase-style exact
- `RR` => rental-style exact
- `TW` => exact-only
- `NU/RR`, `NU**/RR`, `RR NU` => explode into separate NU and RR comparison rows
- `RR/QG`, `RR/QE`, `RR,QG,QF` => keep RR as primary; preserve supplemental modifiers for exact/fallback matching

### Fallback rule
If upstream source lacks the PHCC supplemental modifier but primary modifier matches, allow a primary-only match and send the row to review.

### 3-tier matching strategy
1. Exact: HCPCS + modifier match
2. Proposed-mod-blank: HCPCS match where proposed has no modifier
3. HCPCS-only: code match ignoring modifier (flagged for review)

---

## Rate Cleaning Strategy

### Numeric parse
Attempt strict numeric parsing after stripping `$`, commas, and whitespace.

### Note classes
Classify non-numeric values into:
- `PERCENT_OF_RETAIL` (e.g., "Retail less 25%")
- `NON_BILLABLE`
- `QUOTE_REQUIRED`
- `PERCENT_OF_MEDICARE_ALLOWABLE` (e.g., "Medicare allowable less 20%")
- `PREVAILING_STATE_RATES`
- `PER_TIME_UNIT` (e.g., "per 15 min")
- `COST_INVOICE`
- `UNPARSED_TEXT`
- `BLANK`

Do not invent equivalent numeric values for these notes.

---

## Benchmark Strategy
- Medicare rows use CMS OR/WA as applicable
- Oregon Medicaid rows use OHA
- Washington Medicaid rows without benchmark must remain flagged, not guessed
- Comparison result: ABOVE_BENCHMARK / BELOW_BENCHMARK / EQUAL_TO_BENCHMARK / MISSING_BENCHMARK

---

## Review Queue Rules
Queue rows for manual review when:
- HCPCS cannot be resolved deterministically
- public benchmark is missing but required
- multiple candidate benchmark matches exist
- fallback modifier match is used
- rate value is non-numeric and blocks comparison
- normalized keys collide unexpectedly
- duplicate HCPCS+modifier rows found (e.g., E0248|NU)

---

## Pipeline Execution Order

### Step 1: Clean PHCC source files
```
python clean_phcc_files.py
```
Reads `data/Contract/` → writes `data/cleaned/`

### Step 2: Validate cleaned output
```
python check_clean_output.py
```
Reads `data/cleaned/` → prints diagnostics

### Step 3: Run comparison analysis
```
python analyze_fee_schedules.py
```
Reads `data/cleaned/` + `data/cms/` + `data/INTEGRA_PHP_FFS/` → writes `output/`

---

## Known Issues & Decisions
- **E0248|NU duplicate**: appears twice in both OR and WA participating files — needs dedup policy
- **Category ranges**: 3 L-code umbrella ranges kept as CATEGORY_RANGE — business must decide expand vs keep
- **WA Medicaid benchmark**: no public WA Medicaid fee schedule loaded — flagged MISSING_BENCHMARK
- **Contract files are clean**: 0 OCR corrections needed (unlike earlier OCR-extracted versions)
6. explode PHCC rate-side rows
7. parse numeric vs note-based rates
8. match proposed to current
9. benchmark lower-than-current rows
10. emit audits and review queue

---

## Definition of Done
The skill is done when:
- the master dataset is reproducible
- all PHCC HCPCS anomalies are accounted for
- ranges are expanded
- modifier mapping is explicit
- note-based rate rows are preserved
- unresolved rows are isolated in audit/review outputs
