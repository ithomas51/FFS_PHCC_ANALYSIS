# PHCC Validation Review

## Scope
This review summarizes the output from `phcc_hcpcs_validator.py` run against:

- `PHCC_OR_CONTRACTED.csv`
- `PHCC_OR_PARTICIPATING.csv`
- `PHCC_WA_PARTICIPATING.csv`

---

## High-Level Result
The PHCC files are mostly usable after deterministic cleanup, but they are not comparison-ready yet.

### Key finding
Only **5 PHCC rows remain true manual-review HCPCS problems** after deterministic cleanup rules are applied.

### Why the pipeline is still not ready
The blocking issue is not only invalid single codes. It is also:
- PHCC range rows that must be flattened
- mixed modifier semantics (`NU/RR`, `RR/QE`, `RR,QG,QF`, etc.)
- note-based rate text that blocks naive numeric comparison

---

## Summary By File

### `PHCC_OR_CONTRACTED.csv`
- rows: **269**
- valid HCPCS rows: **225**
- recoverable single-code rows: **41**
- range rows: **1**
- manual-review rows: **2**

Observed issue mix:
- OCR `O` vs `0`: **34**
- hyphen noise: **7**
- unresolved `?`: **2**

Main pattern:
- a large block of wheelchair accessory rows appears OCR-shifted from `K00xx` / `K0xxx` style codes, for example:
  - `KOO17` -> deterministic suggestion `K0017`
  - `KO1O5` -> deterministic suggestion `K0105`

---

### `PHCC_OR_PARTICIPATING.csv`
- rows: **156**
- valid HCPCS rows: **154**
- recoverable single-code rows: **1**
- range rows: **1**
- manual-review rows: **0**

Observed issue mix:
- extra text after code: **1**
- range rows: **1**

Example:
- `A7000\nSuction` -> deterministic suggestion `A7000`
- `A7520-A7522` -> valid range requiring flattening

---

### `PHCC_WA_PARTICIPATING.csv`
- rows: **423**
- valid HCPCS rows: **407**
- recoverable single-code rows: **1**
- range rows: **12**
- manual-review rows: **3**

Observed issue mix:
- range rows: **12**
- hyphen noise: **1**
- unresolved `?`: **3**

Important observation:
Three very broad L-code umbrella ranges appear in WA:
- `L0112-L2861`
- `L3000-L4631`
- `L8300-L8485`

These three ranges alone materially increase row volume after flattening.

---

## Range Expansion Impact

### Current detected PHCC range rows
- OR contracted: **1**
- OR participating: **1**
- WA participating: **12**

### Expansion effect
If all detected PHCC ranges are flattened, they generate approximately:

- OR contracted: **2** atomic codes
- OR participating: **3** atomic codes
- WA participating: **4,621** atomic codes

### Why this matters
The row-count explosion is driven mostly by three broad WA orthotics/prosthetics ranges. The comparison pipeline should therefore:
- expand deterministically
- tag expanded members with range lineage
- deduplicate post-expansion keys carefully

---

## Modifier Findings

### OR contracted distinct modifiers
- `NU`
- `NU/RR`
- `RR`
- one blank modifier row

### OR participating distinct modifiers
- `NU`
- `NU/RR`
- `RR`
- `RR/QE`
- `RR/QG`
- `RR,QG,QF`
- `TW`

### WA participating distinct modifiers
- `NU`
- `NU/RR`
- `NU**/RR`
- `RR`
- `RR NU`
- `RR/QE`
- `RR/QG`
- `RR,QG,QF`

### Interpretation
PHCC modifiers are not a simple one-column exact match problem. Several rows encode:
- combined rental/purchase semantics
- rental plus supplemental clinical/service modifiers
- formatting noise that should be normalized before matching to Integra/CMS/OHA

---

## Rate Note Findings

### OR contracted
Heavy use of:
- `Retail less 25%`
- `Retail less 36%`
- `Retail less 37%`
- `Quote`
- one malformed note-like entry around `$15.40 ...`

### OR participating
Contains:
- numeric rates
- `Retail less 20%`
- `Retail less 25%`
- `Retail less 30%`
- `Non-billable`

### WA participating
Contains:
- numeric rates
- `Retail less 20%`
- `Retail less 25%`
- `Retail less 30%`
- `Retail less 36%`
- `Retail less 37%`
- `Non-billable`
- `Quote`
- `$15.40 per 15 min`
- `Medicare Allowable less 20%`

### Interpretation
A comparison script that treats all rate fields as decimal will fail or produce misleading output. Rate fields must be split into:
- numeric comparison values
- structured note classes
- review-required rows when note text blocks benchmark math

---

## Duplicate Observations
At least one duplicate normalized PHCC key is present in both participating files:

- `E0248` + `NU` appears twice in OR participating
- `E0248` + `NU` appears twice in WA participating

These duplicates should be reviewed before final comparison output is trusted.

---

## Recommended Next Steps

### 1. Lock in deterministic PHCC HCPCS cleanup
Approve these auto-fix classes:
- whitespace cleanup
- trailing hyphen cleanup
- OCR `O` -> `0` in numeric positions
- leading-code extraction where extra description leaks into the HCPCS field

### 2. Keep unresolved question-mark rows in manual review
Do not guess these five unresolved rows.

### 3. Build range expansion before master comparison
This is required, especially for WA orthotics/prosthetics umbrella rows.

### 4. Normalize modifiers into token sets
At minimum support:
- single modifiers
- split rental/purchase rows from `NU/RR` patterns
- RR primary plus supplemental tokens

### 5. Classify note-based pricing before comparing numbers
Create a note taxonomy and preserve note text; do not coerce to decimal.

### 6. Review duplicates after normalization
Confirm whether duplicate `E0248|NU` rows are legitimate duplicates or should be collapsed.

### 7. Only after the above, build the payer comparison table
This reduces the chance of false mismatches and misleading benchmark results.
