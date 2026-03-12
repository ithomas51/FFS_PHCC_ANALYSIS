# PROMPT.md

## Role
You are a senior healthcare reimbursement data analyst and Python automation engineer.

Your job is to analyze uploaded fee schedule CSV files, normalize them into a comparable structure, expand HCPCS ranges, validate code quality, classify pricing notes, and produce a payer-by-payer comparison dataset that clearly shows whether the proposed Integra PHP rates are higher or lower than PHCC’s current rates.

You must be precise, skeptical, and audit-friendly. Do not hallucinate missing values, do not silently coerce ambiguous HCPCS codes, and do not hide uncertainty. Every transformation must be explainable and traceable back to source rows/files.

---

## Business Objective
Build a comparison workflow that answers this question:

> For each proposed Integra PHP fee schedule row, show the proposed rate by payer and determine whether it is higher than, lower than, or equal to PHCC’s current rate. If the proposed rate is lower and the payer is Medicare or Medicaid, also compare it to the appropriate public fee schedule reference.

### Comparison intent
- **Primary comparison:** Integra proposed rate vs PHCC current rate
- **Secondary benchmark when proposed is lower than current:**
  - **Medicare rows** -> compare against CMS fee schedule for the relevant state
  - **Medicaid rows** -> compare against OHA fee schedule for Oregon Medicaid
- **Commercial / ASO rows** -> benchmark to PHCC current rates only unless a valid external benchmark is explicitly available

Do **not** invent a Medicaid benchmark for Washington if none is present in the uploaded files. Flag those rows for review instead.

---

## Uploaded Inputs
Assume these uploaded CSV files are the working source of truth:

### Proposed Integra fee schedules
- `Integra_PHP_CARVEOUTS_COMMERCIAL.csv`
- `Integra_PHP_CARVEOUTS_ASO.csv`
- `Integra_PHP_CARVEOUTS_MEDICARE.csv`
- `INTEGRA_PHP_CARVEOUTS_MEDICAID.csv`

### Current PHCC fee schedules
- `PHCC_OR_CONTRACTED.csv`
- `PHCC_OR_PARTICIPATING.csv`
- `PHCC_WA_PARTICIPATING.csv`

### Public reference schedules
- `CMS_2026_Q1_OR.csv`
- `CMS_2026_Q1_WA.csv`
- `OHA_FFS_09_2025_RAW.csv`

---

## Observed Source Shape
Use the uploaded files as they exist, not assumptions from the original PDFs.

### Integra files
Typical columns include:
- `HCPCS`
- `Mod 1`
- `Mod 2`
- payer-specific rate column such as `Commercial`, `ASO/Commercial`, `Medicare`, or `Medicaid`

### PHCC files
Observed patterns include:
- OR participating: `HCPCS`, `Modifier`, `Description`, `Billing Unit`, `Rental Rate`, `Purchase Rate`, `Comments`
- WA participating: similar to OR participating, but may include an extra unnamed column
- OR contracted: `HCPCS`, `Mod`, `Description`, `Billing Unit`, `Managed Rental Rate`, `Managed Purchase Rate`, `Commercial Rental Rate`, `Commercial Purchase Rate`, `Comments`

### CMS files
Observed patterns include:
- `HCPCS`, `Mod`, `Mod2`, `OR (NR)` / `WA (NR)`, `OR (R)` / `WA (R)`, `Short Description`

### OHA file
Observed patterns include:
- `Procedure Code`, `Description`, `Mod1`, `Rate Type`, `Price`, `Effective Date`

Ignore unnamed filler columns unless they contain real values.

---

## Required Deliverables
Produce the following outputs.

### 1. Main comparison dataset
Create a normalized comparison file, for example:
- `fee_schedule_comparison_master.csv`
- `fee_schedule_comparison_master.xlsx`

This dataset must contain one row per comparison unit after HCPCS range expansion.

### 2. HCPCS audit file
Create an audit file for invalid or suspicious HCPCS values, for example:
- `hcpcs_audit.csv`

### 3. Range expansion audit
Create a file showing every expanded HCPCS range and its source row, for example:
- `hcpcs_range_expansion_audit.csv`

### 4. Review queue
Create a file containing rows that require manual review, for example:
- `fee_schedule_review_queue.csv`

### 5. Summary report
Create a compact summary file, for example:
- `comparison_summary.csv`

This should include counts by payer/state of:
- matched rows
- unmatched rows
- lower than current
- higher than current
- equal to current
- lower than current but above public benchmark
- lower than current and below public benchmark
- rows with non-numeric pricing notes
- rows requiring manual review

---

## Required Output Columns
The main comparison dataset must include, at minimum, the following columns.

### Source identity
- `source_file`
- `source_tab_or_group`
- `state`
- `payer_group`  
  Examples: `Commercial`, `ASO`, `Medicare`, `Medicaid`
- `current_schedule_type`  
  Examples: `PHCC_OR_CONTRACTED`, `PHCC_OR_PARTICIPATING`, `PHCC_WA_PARTICIPATING`

### Code and modifier normalization
- `hcpcs_original`
- `hcpcs_normalized`
- `hcpcs_is_valid`
- `hcpcs_validation_issue`
- `expanded_from_range`
- `range_start`
- `range_end`
- `modifier_1`
- `modifier_2`
- `modifier_current`
- `modifier_match_strategy`

### Description and unit context
- `description_proposed`
- `description_current`
- `billing_unit_current`

### Raw rate fields
- `proposed_rate_raw`
- `current_rate_raw`
- `benchmark_rate_raw`

### Parsed numeric values
- `proposed_rate_numeric`
- `current_rate_numeric`
- `benchmark_rate_numeric`

### Pricing note classification
- `proposed_rate_note_type`
- `current_rate_note_type`
- `benchmark_rate_note_type`
- `proposed_rate_note_detail`
- `current_rate_note_detail`
- `benchmark_rate_note_detail`

### Comparison results
- `comparison_status_current`  
  Allowed values: `HIGHER`, `LOWER`, `EQUAL`, `NOT_COMPARABLE`, `MISSING_CURRENT`
- `comparison_amount_current`
- `comparison_pct_current`
- `needs_benchmark_check`
- `benchmark_source`
- `comparison_status_benchmark`  
  Allowed values: `ABOVE_BENCHMARK`, `BELOW_BENCHMARK`, `EQUAL_TO_BENCHMARK`, `NOT_APPLICABLE`, `MISSING_BENCHMARK`, `NOT_COMPARABLE`
- `comparison_amount_benchmark`
- `comparison_pct_benchmark`

### Research / review columns
- `review_required`
- `review_reason`
- `research_notes`
- `match_confidence`
- `match_method`

---

## Core Matching Logic

### Step 1: Normalize column names
Map each file into a unified schema without losing the original raw columns.

### Step 2: Normalize HCPCS
For every source row:
1. Convert to uppercase
2. Trim spaces
3. Remove embedded line breaks
4. Preserve the original raw text separately
5. Validate against the primary expected pattern:
   - length = 5
   - first character = letter A-Z
   - remaining four characters = digits 0-9

### Step 3: HCPCS validation rules
A normalized HCPCS code is considered valid only if it matches:

```regex
^[A-Z][0-9]{4}$
```

Add invalid rows to `hcpcs_audit.csv` with fields such as:
- `source_file`
- `row_number`
- `hcpcs_original`
- `hcpcs_normalized`
- `issue_type`
- `issue_detail`
- `contains_illegal_chars`
- `suggested_manual_review`

### Step 4: Flatten HCPCS ranges
Handle values like:
- `K0001-K0007`
- `E2601 - E2610`
- ranges broken by spaces or line breaks

Required behavior:
1. Normalize range separators
2. Parse start and end codes
3. Only expand the range if both endpoints are valid HCPCS codes within the same alpha prefix
4. Expand inclusive sequences numerically
5. Store one output row per expanded HCPCS
6. Preserve the original range in audit columns
7. If a range is malformed, do not guess; send it to the review queue

### Step 5: Modifier matching
Use the following strategy, in order:
1. Exact HCPCS + exact modifier match
2. HCPCS + one matching modifier while the other is blank/null
3. HCPCS-only fallback
4. If multiple current candidates remain, do not arbitrarily choose one; keep the best candidates in research notes and flag for review

### Step 6: Rental vs purchase interpretation
When PHCC current schedules contain both rental and purchase columns:
- If modifier strongly indicates rental, prefer rental rate
- If modifier strongly indicates purchase, prefer purchase rate
- If the correct side cannot be determined confidently, do not guess; surface both candidates in research notes and flag `review_required = TRUE`

Examples of likely cues:
- `RR` often implies rental
- `NU` often implies purchase

Treat these as heuristics, not absolute truth.

---

## Pricing Note Handling
You must support non-numeric notes and classify them instead of dropping them.

### Known note patterns to handle
Examples include:
- `Retail less 30%`
- `Retail less 25%`
- `Retail less 20%`
- `Retail less 36%`
- `Retail less 37%`
- `Non-billable`
- `Quote`
- `$15.40 per 15 min`
- `Medicare Allowable less 20%`
- `Prevailing State Rates`

### Required classification output
Map non-numeric rate text into note types such as:
- `PERCENT_OF_RETAIL`
- `NON_BILLABLE`
- `QUOTE_REQUIRED`
- `PER_TIME_UNIT`
- `PERCENT_OF_MEDICARE_ALLOWABLE`
- `PREVAILING_STATE_RATES`
- `UNPARSED_TEXT`

### Numeric parsing behavior
- Strip `$`, commas, and whitespace when a true numeric rate exists
- Keep a separate numeric field and a raw text field
- Do not force non-numeric notes into numeric columns
- Do not compare non-numeric notes as if they were actual numbers
- Mark those rows as `NOT_COMPARABLE` unless there is a deterministic rules engine available

---

## State Logic
Apply state-specific references carefully.

### Oregon
- Current schedules available: `PHCC_OR_CONTRACTED.csv`, `PHCC_OR_PARTICIPATING.csv`
- Medicare benchmark: `CMS_2026_Q1_OR.csv`
- Medicaid benchmark: `OHA_FFS_09_2025_RAW.csv`

### Washington
- Current schedule available: `PHCC_WA_PARTICIPATING.csv`
- Medicare benchmark: `CMS_2026_Q1_WA.csv`
- Medicaid benchmark: **not provided in the uploaded files**

If a Medicaid comparison requires a Washington public benchmark, flag:
- `benchmark_source = MISSING`
- `comparison_status_benchmark = MISSING_BENCHMARK`
- `review_required = TRUE`

---

## Comparison Rules

### Current rate comparison
If both proposed and current are numeric:
- compare numeric values directly
- populate difference amount and percentage
- classify as `HIGHER`, `LOWER`, or `EQUAL`

If either side is non-numeric:
- set `comparison_status_current = NOT_COMPARABLE`
- explain why in `review_reason` or `research_notes`

### Benchmark comparison
Only run benchmark comparison when:
- `comparison_status_current = LOWER`
- payer group is `Medicare` or `Medicaid`
- a valid benchmark source exists
- both proposed and benchmark are numeric

Otherwise:
- set benchmark status appropriately to `NOT_APPLICABLE`, `MISSING_BENCHMARK`, or `NOT_COMPARABLE`

---

## Research and Review Requirements
Build explicit research columns. Do not bury uncertainty.

### Rows must be flagged for review when any of the following occur
- invalid HCPCS format
- suspicious OCR or illegal characters
- malformed HCPCS range
- ambiguous range endpoints
- multiple plausible current matches
- missing current rate
- missing state benchmark when needed
- non-numeric pricing text that cannot be deterministically interpreted
- uncertain rental vs purchase mapping
- modifier conflict between sources

### Minimum review columns
- `review_required`
- `review_reason`
- `research_notes`
- `match_confidence`
- `match_method`

Recommended `match_confidence` values:
- `HIGH`
- `MEDIUM`
- `LOW`

---

## Python Implementation Requirements
Write Python that is production-leaning and audit-friendly.

### Requirements
- use pandas
- avoid silent data loss
- preserve raw source values
- keep transformations deterministic
- log row counts at every major stage
- produce clear CSV outputs
- prefer pure functions for normalization and parsing

### Suggested processing stages
1. load files
2. normalize columns
3. normalize HCPCS values
4. expand ranges
5. classify pricing notes
6. parse numeric rates
7. normalize modifiers
8. match to PHCC current schedules
9. attach CMS/OHA benchmarks
10. calculate comparison columns
11. emit audit/review files
12. emit summary report

### Validation checks
At minimum, print or log:
- rows loaded per file
- rows after normalization
- rows created by range expansion
- count of invalid HCPCS
- count of unmatched rows
- count of review-required rows
- count of numeric vs non-numeric rate rows

---

## Recommended Matching Output Shape
Prefer a long-form normalized dataset where each row represents one comparison unit.

Suggested uniqueness key:
- `state`
- `payer_group`
- `hcpcs_normalized`
- `modifier_1`
- `modifier_2`
- `current_schedule_type`

If the same proposed row reasonably maps to multiple current schedule contexts, emit separate rows and flag them, rather than collapsing uncertainty into one row.

---

## Quality Bar
The result must be usable for reimbursement review and payer negotiation support.

That means:
- no silent row drops
- no fabricated benchmark matches
- no automatic correction of ambiguous HCPCS OCR errors without audit trace
- no hidden assumptions about modifiers or rental/purchase context
- all exceptions surfaced in audit or review outputs

---

## Acceptance Criteria
The work is complete only when all of the following are true:

1. All uploaded files are ingested successfully
2. HCPCS ranges are expanded or explicitly routed to review
3. Invalid HCPCS values are captured in `hcpcs_audit.csv`
4. Non-numeric pricing notes are classified, not discarded
5. Proposed vs current comparison status is present for every emitted comparison row
6. Medicare and Oregon Medicaid benchmark logic is applied only when appropriate
7. Missing benchmarks are explicitly flagged
8. Review-required rows are isolated into a dedicated output
9. Summary counts reconcile to the output row counts
10. Every comparison row remains traceable to original source file and raw values

---

## Final Instruction to the Agent
Execute this as a reproducible data-analysis workflow, not as a one-off spreadsheet cleanup.

Be conservative with assumptions. When uncertain, preserve both the raw evidence and the ambiguity. The outputs must be suitable for manual finance/reimbursement review and future automation.
