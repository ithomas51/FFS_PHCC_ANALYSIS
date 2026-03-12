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

---

## Inputs Expected

### Proposed schedules
- `Integra_PHP_CARVEOUTS_COMMERCIAL.csv`
- `Integra_PHP_CARVEOUTS_ASO.csv`
- `Integra_PHP_CARVEOUTS_MEDICARE.csv`
- `INTEGRA_PHP_CARVEOUTS_MEDICAID.csv`

### Current schedules
- `PHCC_OR_CONTRACTED.csv`
- `PHCC_OR_PARTICIPATING.csv`
- `PHCC_WA_PARTICIPATING.csv`

### Public benchmarks
- `CMS_2026_Q1_OR.csv`
- `CMS_2026_Q1_WA.csv`
- `OHA_FFS_09_2025_RAW.csv`

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

---

## Core Principles
1. Never silently repair ambiguous codes
2. Preserve raw values before cleaning
3. Separate deterministic cleanup from manual-review logic
4. Expand ranges before final matching
5. Normalize modifiers into tokens before comparison
6. Separate numeric rates from note-based rates
7. Keep an audit trail for every transformation

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
- `L0112-L2861`

Rules:
- expand to one row per member code
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

---

## Rate Cleaning Strategy

### Numeric parse
Attempt strict numeric parsing after stripping `$`, commas, and whitespace.

### Note classes
Classify non-numeric values into:
- `RETAIL_LESS_PCT`
- `NON_BILLABLE`
- `QUOTE`
- `PER_15_MIN_NOTE`
- `MEDICARE_ALLOWABLE_LESS_PCT`
- `OTHER_NOTE`
- `BLANK`

Do not invent equivalent numeric values for these notes.

---

## Benchmark Strategy
- Medicare rows use CMS OR/WA as applicable
- Oregon Medicaid rows use OHA
- Washington Medicaid rows without benchmark must remain flagged, not guessed

---

## Review Queue Rules
Queue rows for manual review when:
- HCPCS cannot be resolved deterministically
- public benchmark is missing but required
- multiple candidate benchmark matches exist
- fallback modifier match is used
- rate value is non-numeric and blocks comparison
- normalized keys collide unexpectedly

---

## Recommended Implementation Order
1. detect columns
2. normalize raw fields
3. validate and repair HCPCS
4. expand ranges
5. normalize modifiers
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
