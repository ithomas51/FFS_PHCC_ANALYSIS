# PLAN.md

## Project
PHCC / Integra Fee Schedule Comparison Pipeline

## Goal
Create an auditable workflow that cleans uploaded fee schedule CSVs, flattens HCPCS ranges, normalizes modifiers, profiles note-based pricing, and produces a payer-by-payer comparison between Integra proposals and PHCC current schedules, with CMS/OHA public benchmark checks where applicable.

---

## What Is Already Known From The Uploaded Files

### File coverage
Present now:
- Integra commercial / ASO / Medicare / Medicaid CSVs
- PHCC OR contracted / OR participating / WA participating CSVs
- CMS WA and OR Q1 2026 CSVs
- OHA Medicaid CSV

### Confirmed source issues
- PHCC contains OCR-style HCPCS corruption
- PHCC contains range rows that must be expanded
- PHCC contains mixed modifier formats
- PHCC contains non-numeric pricing notes that cannot be coerced safely

---

## PHASE 1 — Intake and column detection
### Objective
Standardize each file into a known schema without losing raw source columns.

### Tasks
1. detect file type by filename and observed columns
2. preserve original column names
3. map into canonical fields:
   - `hcpcs_raw`
   - `modifier_raw`
   - `description_raw`
   - `billing_unit_raw`
   - `rate_raw_*`
4. drop empty unnamed filler columns only after verifying they contain no real values

### Done when
- every file has a schema mapping
- source rows retain traceability back to filename and original row number

---

## PHASE 2 — PHCC HCPCS audit and deterministic cleanup
### Objective
Validate PHCC HCPCS values before any comparison logic is attempted.

### Tasks
1. uppercase and whitespace normalize HCPCS
2. validate against `^[A-Z][0-9]{4}$`
3. classify issues:
   - valid
   - hyphen noise
   - OCR `O` vs `0`
   - extra text after code
   - range
   - question mark / unresolved
4. emit audit rows with suggested corrections where deterministic

### Decision rules
- deterministic fix => keep and log
- unresolved => send to review queue

### Done when
- PHCC audit file exists
- every invalid-looking PHCC code is either fixed deterministically or isolated for manual review

---

## PHASE 3 — HCPCS range expansion
### Objective
Convert one-to-many HCPCS range rows into atomic comparison rows.

### Tasks
1. normalize range text
2. parse start/end members
3. expand sequential members
4. carry forward:
   - description
   - modifier
   - rate values
   - comments
   - payer/state context
5. generate range-expansion audit

### Known impact from current files
Range expansion is non-trivial because PHCC WA contains broad umbrella ranges, including:
- `L0112-L2861`
- `L3000-L4631`
- `L8300-L8485`

### Done when
- all requested ranges are flattened into atomic HCPCS rows
- the original range identity remains traceable

---

## PHASE 4 — Modifier normalization and row explosion
### Objective
Create a stable modifier key and a comparison-ready row set.

### Tasks
1. canonicalize modifiers into ordered tokens
2. map:
   - `NU` -> purchase
   - `RR` -> rental
   - `NU/RR`, `NU**/RR`, `RR NU` -> explode into separate NU and RR rows
   - `RR/QG`, `RR/QE`, `RR,QG,QF` -> retain RR as primary with supplemental tokens
3. add:
   - `modifier_primary`
   - `modifier_secondary_tokens`
   - `modifier_match_key`
   - `modifier_expansion_strategy`

### Done when
- PHCC modifier values are normalized consistently
- split semantic rows are materialized explicitly instead of being implied

---

## PHASE 5 — Rate normalization
### Objective
Separate numeric reimbursement from note-based pricing statements.

### Tasks
1. parse numeric rates strictly
2. classify note text
3. preserve raw text and note class
4. do not invent numeric equivalents

### Special note classes to support
- retail-less percentages
- non-billable
- quote
- per-15-minute notes
- Medicare-allowable-less percentages

### Done when
- each rate field is clearly numeric or clearly categorized as a note

---

## PHASE 6 — Comparison build
### Objective
Join proposed rows to PHCC current rows using a defensible key.

### Proposed composite key
- `state`
- `payer_group`
- `hcpcs_key`
- `modifier_match_key`
- `rate_side`

### Tasks
1. normalize Integra modifiers
2. normalize CMS/OHA modifiers
3. build proposed rows
4. build PHCC current rows
5. match exact first, fallback to primary-only modifier where justified
6. compute higher/lower/equal vs current

### Done when
- comparison rows can be explained from source data without hidden logic

---

## PHASE 7 — Benchmark checks
### Objective
When proposed < current, compare against public benchmarks.

### Tasks
1. Medicare -> CMS OR/WA
2. Oregon Medicaid -> OHA
3. Washington Medicaid without public benchmark -> flag missing benchmark
4. preserve benchmark match confidence and ambiguity notes

### Done when
- benchmark comparisons exist only where justified by source coverage

---

## PHASE 8 — QA and exception review
### Objective
Prevent silent bad joins or misleading comparisons.

### QA checks
- duplicate normalized PHCC keys
- unresolved HCPCS values
- range expansion counts
- rows blocked by note-only pricing
- benchmark missing where required
- fallback modifier matches
- duplicate candidate benchmark rows

### Done when
- all exceptions are visible in review outputs
- no suspicious rows are silently dropped

---

## Immediate Next Build Steps
1. use the PHCC validator results to approve deterministic fixes
2. define the exact `hcpcs_key + modifier_match_key + rate_side` join contract
3. implement range expansion as a reusable function
4. build PHCC row explosion for rate-side + modifier-side semantics
5. normalize Integra/CMS/OHA modifiers to the same token model
6. only then build the master comparison table

---

## Acceptance Criteria
The project is ready for business review only when:
- PHCC HCPCS anomalies are fully audited
- requested ranges are flattened
- modifiers are normalized and mapped
- note-based pricing is preserved instead of guessed
- lower-than-current benchmark checks are applied consistently
- unresolved exceptions are isolated in a review queue
