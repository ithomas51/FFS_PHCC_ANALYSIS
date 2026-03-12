# PLAN.md - updates
## Rural vs Non-Rural: Full Analysis

### What the data shows

**CMS DMEPOS fee schedules** (CMS_2026_Q1_OR.csv, CMS_2026_Q1_WA.csv) have **two rate columns each**:

| State | Non-Rural column | Rural column |
|---|---|---|
| Oregon | `OR (NR)` | `OR (R)` |
| Washington | `WA (NR)` | `WA (R)` |

The Rural and Non-Rural rates often differ significantly. Examples from OR data:
- `A4595` (TENS supplies): NR = $11.40, **R = $27.22** (Rural is 139% higher)
- `A7005` (Nebulizer): NR = $11.77, **R = $30.13** (Rural is 156% higher)  
- `A4604` (Tubing): NR = $50.66, **R = $68.75** (Rural is 36% higher)
- Many codes have **R = 0** (no rural rate at all, e.g., most supplies/accessories)

**Neither the PHCC contracts nor the Integra proposed schedules** distinguish Rural from Non-Rural — they each have a single rate per HCPCS/modifier. So you're correct: the proposed rate is one flat number regardless of rurality.

### Current behavior

The script **only loads Non-Rural** (`NR`) as the CMS benchmark:

```python
cms_or_lk = load_cms(FILES["cms_or"], "OR (NR)", "OR")
cms_wa_lk = load_cms(FILES["cms_wa"], "WA (NR)", "WA")
```

Rural rates are completely ignored. This means:
- If a proposed rate is above the NR benchmark but **below** the Rural benchmark, that's invisible
- If a proposed rate is below NR but **above** Rural, that context is missing too
- For codes where NR = 0 but Rural > 0 (e.g., `A4636|NU,KE` where NR = 0, R = $4.95), the benchmark shows "NOT_FOUND" when a real CMS rate actually exists

### What needs to change

1. **`load_cms()` should load BOTH columns** — return both NR and R rates per key
2. **Comparison output** should include both `cms_benchmark_nr` and `cms_benchmark_r` columns on every row
3. **A dedicated "Rural vs Non-Rural Benchmark" XLSX tab** should show side-by-side: proposed rate, PHCC current rate, CMS NR rate, CMS R rate, delta vs NR, delta vs R
4. **Benchmark status** should be evaluated against both — a code could be `BELOW_BENCHMARK` for NR but `ABOVE_BENCHMARK` for Rural or vice versa

### Is Non-Rural always used?

**Yes, currently.** And for many codes it's the only available CMS rate (Rural = 0). But for the subset of codes that DO have Rural rates, the Rural rate is typically **higher** than Non-Rural (rural areas get a surcharge). This means using only NR is the more conservative benchmark — if a proposed rate beats NR, it almost certainly beats Rural too. But for transparency and completeness, both should be shown.

---

Here is the updated PLAN.md incorporating this plus the Phase 6 matching rewrite from our previous discussion. Since I can't edit files directly in Ask mode, here's the complete replacement content:

```markdown
# PLAN.md

## Project
PHCC / Integra Fee Schedule Comparison Pipeline

## Goal
Create an auditable workflow that cleans uploaded fee schedule CSVs, flattens HCPCS ranges, normalizes modifiers, profiles note-based pricing, and produces a payer-by-payer comparison between Integra proposals and PHCC current schedules, with CMS/OHA public benchmark checks where applicable.

---

## Workspace Layout (current)

```
PHCC/
  scripts/                     # All runnable scripts live here
    analyze_fee_schedules.py   # v2 main comparison pipeline
    clean_phcc_files.py        # PHCC source cleaner
    check_clean_output.py      # Validation diagnostic
    run_clean_and_check.ps1    # PowerShell runner
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
  output/                      # Output from analyze_fee_schedules.py
tests/
  test_fee_schedules.py        # Unit + integration tests
  phcc_hcpcs_validator.py      # HCPCS profiling utility
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
- analyze_fee_schedules.py: 3-tier matching (exact → proposed-mod-blank → HCPCS-only)
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

## PHASE 6 — Multi-tier matching engine (REWRITE REQUIRED)
### Status: ⚠️ NEEDS REWRITE — current logic drops valid comparisons

### Objective
For each proposed Integra row, produce **all meaningful comparisons** against PHCC current rates and CMS benchmarks, not just the first match found.

### Problem statement
The current matching engine has four gaps:

1. **Single-match-only**: Returns after the *first* PHCC match. If Integra proposes `E0950` with no modifier and PHCC has both `E0950|NU` and `E0950|RR`, only one is compared — the other is silently dropped.
2. **No cross-modifier fallback for PHCC**: If Integra proposes `A4217|AU` and PHCC has `A4217|NU` only, there is no comparison. The code falls through to an arbitrary pick with LOW confidence but does not explicitly try semantically related modifiers.
3. **CMS benchmark only tries exact + blank**: If Integra has `RR` and CMS only has `NU` for that code, the benchmark misses entirely. DMEPOS commonly has purchase-only CMS rates.
4. **No code-level aggregate**: When no modifier match exists, there's no row showing "here's what this HCPCS costs across all modifiers in PHCC" as a reference.

### New matching strategy: exhaustive tiered approach

For each proposed Integra row (HCPCS + modifier), emit **multiple comparison rows** — one per tier that produces a result. Each row is tagged with its `match_tier` so the executive summary can filter by confidence.

#### PHCC matching tiers (emit all that hit)

| Tier | Key | Confidence | Emit when | Output row tag |
|---|---|---|---|---|
| T1 | `HCPCS + exact modifier` | HIGH | Proposed mod == PHCC mod | `EXACT_HCPCS_MOD` |
| T2 | `HCPCS + proposed-mod → PHCC-blank` | MEDIUM | PHCC has blank mod for this code, proposed has NU/RR/etc. | `PROPOSED_MOD_PHCC_BLANK` |
| T3 | `HCPCS + cross-modifier` | MEDIUM | No exact match; try related mods (NU↔RR, or any available mod for same HCPCS) | `CROSS_MOD_REFERENCE` |
| T4 | `HCPCS only (all mods)` | LOW | No modifier match at all; emit one row per PHCC modifier variant for this code | `HCPCS_ALL_MODS` |
| — | `HCPCS not found` | NONE | Code absent from PHCC entirely | `NO_MATCH` |

**Rules:**
- T1 is the primary comparison row (used for executive summary roll-ups)
- T2–T4 are reference rows (flagged `is_reference_match = True`)
- If T1 succeeds, T2–T4 are still emitted as supplemental context but excluded from summary counts
- If T1 fails, the **best available tier** becomes the primary comparison (T2 > T3 > T4)
- T4 emits **one row per distinct PHCC modifier** for that HCPCS — not just the first candidate
- All rows carry `match_tier`, `match_confidence`, `is_primary_match` columns

**Cross-modifier resolution order (T3):**

| Proposed mod | Try in order |
|---|---|
| `NU` | `RR`, `""` (blank) |
| `RR` | `NU`, `""` (blank) |
| `AU` | `NU`, `""` (blank) |
| `KF` | `NU`, `""` (blank) |
| other | `NU`, `RR`, `""` (blank) |
| `""` (blank) | `NU`, `RR` |

#### CMS benchmark matching tiers

| Tier | Key tried | Fallback |
|---|---|---|
| B1 | `code|exact_mod` | — |
| B2 | `code|NU` | Purchase rate is the most common CMS rate |
| B3 | `code|RR` | Rental if purchase unavailable |
| B4 | `code|` (blank) | Unmodified rate if exists |
| — | Not found | `NOT_FOUND_IN_CMS` |

**Rules:**
- For Medicare benchmark: try B1 → B2 → B3 → B4
- For OHA Medicaid: same cascade (already partially implemented for `code|NU`)
- Tag each benchmark with `benchmark_match_tier` so it's clear whether the benchmark was exact or fallback
- If benchmark used a different modifier than proposed, flag `benchmark_mod_mismatch = True`

#### OHA Medicaid benchmark matching tiers

| Tier | Key tried |
|---|---|
| B1 | `code|exact_mod` |
| B2 | `code|NU` |
| B3 | `code|` (blank) |
| — | Not found → `NOT_FOUND_IN_OHA` |
| — | WA state → `WA_MEDICAID_NOT_PROVIDED` |

### Output schema additions

New columns added to master comparison output:

| Column | Type | Description |
|---|---|---|
| `match_tier` | str | `T1`, `T2`, `T3`, `T4`, or `NO_MATCH` |
| `is_primary_match` | bool | True for the best-tier match used in summary roll-ups |
| `is_reference_match` | bool | True for supplemental comparison rows (T2–T4 when T1 exists) |
| `cross_mod_used` | str | The PHCC modifier actually used when different from proposed |
| `all_phcc_mods_available` | str | Comma-separated list of all modifiers found for this HCPCS in PHCC |
| `benchmark_match_tier` | str | `B1`, `B2`, `B3`, `B4`, or `NOT_FOUND` |
| `benchmark_mod_used` | str | CMS/OHA modifier actually matched |
| `benchmark_mod_mismatch` | bool | True if benchmark mod differs from proposed mod |

### Example scenarios

**Scenario A: Integra proposes `E0950|NU`, PHCC has `E0950|NU` and `E0950|RR`**
- T1 row: E0950|NU vs PHCC E0950|NU → HIGH, `is_primary_match=True`
- T4 row: E0950|NU vs PHCC E0950|RR → LOW, `is_reference_match=True`

**Scenario B: Integra proposes `A4217|AU`, PHCC has `A4217|NU` only**
- T1: no match (AU ≠ NU)
- T2: no match (no blank-mod PHCC row)
- T3 row: A4217|AU vs PHCC A4217|NU → MEDIUM, `cross_mod_used=NU`, `is_primary_match=True`
- CMS benchmark: B1 `A4217|AU` found → exact benchmark

**Scenario C: Integra proposes `E0637|NU`, PHCC has `E0637|NU`, CMS has no `E0637|NU` but has `E0637|RR`**
- T1 row: E0637|NU vs PHCC E0637|NU → HIGH, `is_primary_match=True`
- Benchmark: B1 miss → B2 `E0637|NU` miss → B3 `E0637|RR` hit → `benchmark_match_tier=B3`, `benchmark_mod_mismatch=True`

**Scenario D: Integra proposes `L3999|NU`, PHCC has no L3999 at all**
- `NO_MATCH`, review queue, no comparison possible

**Scenario E: Integra proposes `A4450|` (blank mod), PHCC has `A4450|NU`, CMS has `A4450|AU` + `A4450|AV` + `A4450|AW`**
- T1: no match (blank ≠ NU)
- T2: no match (no blank-mod PHCC row)
- T3 row: A4450|blank vs PHCC A4450|NU → MEDIUM, `cross_mod_used=NU`, `is_primary_match=True`
- CMS benchmark: B1 `A4450|` miss → B2 `A4450|NU` miss → B3 `A4450|RR` miss → B4 `A4450|` miss → `NOT_FOUND_IN_CMS`

### Implementation notes
- `match_proposed_to_current()` changes from returning **one dict** to returning **a list of dicts** (one per tier that matched)
- `_process_one_proposed()` iterates over the returned list instead of using a single result
- Executive summary counts only rows where `is_primary_match=True`
- Review queue includes all rows where `is_reference_match=True` that show a materially different rate than the primary
- `lookup_benchmark()` expands its key cascade and returns matching tier metadata

### ⚠️ Critical integration gap (unchanged)
analyze_fee_schedules.py reads **raw Contract files** and reimplements cleanup inline.
It does NOT consume the cleaned CSVs from Phase 2.
Risk: logic divergence between `clean_phcc_files.py` and analyze_fee_schedules.py.

**Action required**: Refactor analyze_fee_schedules.py to load from `data/cleaned/` outputs.

---

## PHASE 7 — Benchmark checks (Rural + Non-Rural)
### Status: ⚠️ NEEDS UPDATE — Rural rates not loaded, cascade logic expanded in Phase 6

### Objective
When proposed < current, compare against public benchmarks. Show **both Rural and Non-Rural** CMS rates.

### Problem: Rural rates completely ignored
CMS DMEPOS fee schedules have two rate columns per state:
- `OR (NR)` / `OR (R)` — Oregon Non-Rural / Rural
- `WA (NR)` / `WA (R)` — Washington Non-Rural / Rural

**Neither** Integra proposed schedules **nor** PHCC current contracts distinguish Rural from Non-Rural — they have a single flat rate. The current script only loads `(NR)` columns. Rural `(R)` rates are significant:
- Many codes: Rural = 0 (no rural rate, NR is the only CMS rate)
- Many DMEPOS codes: Rural > Non-Rural (rural surcharge), sometimes dramatically
  - `A4595`: NR=$11.40, R=$27.22 (+139%)  
  - `A7005`: NR=$11.77, R=$30.13 (+156%)  
  - `A4604`: NR=$50.66, R=$68.75 (+36%)
- Some codes: Rural-only rate exists (NR=0, R>0), e.g., `A4636|NU,KE`

### Required changes

#### `load_cms()` — load both NR and R columns
Currently returns: `{key: {"rate": nr_rate, ...}}`
Change to: `{key: {"rate_nr": nr_rate, "rate_r": r_rate, ...}}`

Load both columns:
```python
def load_cms(path, nr_col, r_col, state):
    ...
    rate_nr = safe_float(r.get(nr_col, ""))
    rate_r  = safe_float(r.get(r_col, ""))
    records[key] = {"rate_nr": rate_nr, "rate_r": rate_r, ...}
```

Call sites:
```python
cms_or_lk = load_cms(FILES["cms_or"], "OR (NR)", "OR (R)", "OR")
cms_wa_lk = load_cms(FILES["cms_wa"], "WA (NR)", "WA (R)", "WA")
```

#### `lookup_benchmark()` — return both Rural and Non-Rural
Expand return tuple to include both rates and separate status:
```
(bench_nr, bench_r, bench_source, bench_match_tier, bench_mod_used, 
 bench_status_nr, bench_status_r)
```

#### Output columns for benchmarks
| Column | Description |
|---|---|
| `cms_benchmark_nr` | CMS Non-Rural rate |
| `cms_benchmark_r` | CMS Rural rate |
| `cms_benchmark_source` | Source file |
| `cms_benchmark_match_tier` | B1/B2/B3/B4 |
| `cms_benchmark_mod_used` | Actual CMS modifier matched |
| `cms_benchmark_mod_mismatch` | True if CMS mod differs from proposed |
| `benchmark_status_nr` | ABOVE/BELOW/EQUAL/MISSING vs Non-Rural |
| `benchmark_status_r` | ABOVE/BELOW/EQUAL/MISSING vs Rural |
| `delta_vs_cms_nr` | Proposed − CMS NR |
| `delta_vs_cms_r` | Proposed − CMS R |
| `pct_delta_vs_cms_nr` | % difference vs NR |
| `pct_delta_vs_cms_r` | % difference vs R |

#### Benchmark evaluation rules
- If CMS R = 0 (no rural rate): `benchmark_status_r = "NO_RURAL_RATE"`
- Benchmark status is computed independently for NR and R
- A proposed rate could be `BELOW_BENCHMARK` for NR but `ABOVE_BENCHMARK` for R — both are shown
- Executive summary uses Non-Rural as the primary benchmark flag (most conservative)
- Rural comparison is supplemental context

### OHA Medicaid
OHA has a single `Price` column — no Rural/Non-Rural distinction.
No change needed for OHA beyond the modifier cascade from Phase 6.

---

## PHASE 8 — QA and exception review
### Status: ✅ COMPLETE (will gain new triggers from Phase 6 + 7)

### Objective
Prevent silent bad joins or misleading comparisons.

### Implementation
- `review_required` boolean flag + `review_reason` concatenated text
- Triggers: invalid HCPCS, missing benchmark, fallback modifier match, note-only rate, duplicate keys

### New review triggers from Phase 6 + 7
- `CROSS_MOD_REFERENCE` used as primary match (no exact or blank-mod match existed)
- `HCPCS_ALL_MODS` used as primary match (no modifier-level match at all)
- `benchmark_mod_mismatch = True` (benchmark rate is from a different modifier)
- Reference match rate differs from primary match rate by >10%
- `benchmark_status_nr ≠ benchmark_status_r` (proposed is below one but above the other)
- CMS Rural-only rate exists but NR = 0

### Output
- `fee_schedule_review_queue.csv`

---

## PHASE 9 — XLSX output enhancement
### Status: 🔲 NOT STARTED

### Objective
Produce an executive-ready Excel workbook with formatting, conditional styling, and frozen panes.

### Tasks
1. Refactor analyze_fee_schedules.py to consume cleaned PHCC CSVs instead of raw files
2. Run end-to-end and validate output in `output/`
3. Enhance XLSX output with:
   - **Executive summary tab**: payer/state breakdown counts, % higher/lower/equal, average deltas (primary matches only)
   - **Conditional formatting**: green for HIGHER, red for LOWER/BELOW_BENCHMARK, yellow for NOT_COMPARABLE/MISSING
   - **Frozen panes**: lock header row + HCPCS/modifier columns
   - **Column width auto-fit**: readable without manual resizing
   - **Number formatting**: currency for rate columns, percentage for delta columns
   - **Named ranges / filters**: auto-filter on all data tabs
   - **Review queue tab**: filtered view of flagged rows with color coding
   - **Benchmark comparison tab**: only rows where proposed < current, showing benchmark result
   - **Rural vs Non-Rural tab**: side-by-side CMS NR and R benchmark comparison
   - **Reference matches tab**: non-primary comparison rows for cross-modifier context
4. Add data validation annotations for note-based pricing columns
5. Add a "Data Sources" tab documenting file origins, row counts, and processing date

### XLSX tab structure (proposed)

| Tab | Content | Formatting |
|---|---|---|
| Executive Summary | Payer × state matrix, % higher/lower, avg delta (primary only) | Conditional fill, bold headers |
| All Comparisons | Full master dataset (primary matches) | Frozen row 1 + cols A-C, auto-filter |
| Reference Matches | T2–T4 supplemental context rows | Gray header, match_tier column highlighted |
| Lower Than Current | Filtered: proposed < current (primary) | Red fill on delta |
| Below Benchmark | Filtered: below CMS/OHA floor (NR as primary) | Red bold |
| Rural vs Non-Rural | All rows with both NR + R CMS rates: proposed, PHCC current, CMS NR, CMS R, delta vs each | Conditional: green if above both, red if below both, yellow if split |
| Review Queue | Flagged rows (primary + reference anomalies) | Yellow fill, review_reason column |
| Audit Trail | HCPCS audit + range expansion | Grouped by issue type |
| Data Sources | File inventory, row counts, date | Static reference |

### Rural vs Non-Rural tab detail
This tab addresses the fact that Integra proposed rates and PHCC current rates do NOT distinguish Rural from Non-Rural. For Medicare payer rows, show:

| Column | Source |
|---|---|
| HCPCS | Proposed |
| Mod | Proposed |
| Description | HCPCS ref |
| Proposed Rate | Integra |
| PHCC Current Rate | PHCC (primary match) |
| CMS Non-Rural Rate | `cms_benchmark_nr` |
| CMS Rural Rate | `cms_benchmark_r` |
| Delta vs NR | Proposed − NR |
| Delta vs R | Proposed − R |
| % Delta vs NR | % difference |
| % Delta vs R | % difference |
| Status vs NR | ABOVE/BELOW/EQUAL/MISSING |
| Status vs R | ABOVE/BELOW/EQUAL/NO_RURAL_RATE |
| State | OR / WA |

**Conditional formatting:**
- Green: proposed ≥ both NR and R
- Red: proposed < both NR and R  
- Yellow: proposed between NR and R (split status)
- Gray: no CMS rate available

### Done when
- XLSX opens in Excel with no manual formatting needed
- Executive tab is decision-ready (uses primary matches only)
- Rural vs Non-Rural tab shows both CMS benchmarks side-by-side for every Medicare comparison
- Reference matches available in separate tab for deep-dive
- All tabs have frozen headers and auto-filters
- Conditional formatting highlights action items

---

## Immediate Next Steps
1. ~~use the PHCC validator results to approve deterministic fixes~~ ✅
2. ~~define the exact `hcpcs_key + modifier_match_key + rate_side` join contract~~ ✅
3. ~~implement range expansion as a reusable function~~ ✅
4. ~~build PHCC row explosion for rate-side + modifier-side semantics~~ ✅
5. ~~normalize Integra/CMS/OHA modifiers to the same token model~~ ✅
6. ~~build the master comparison table~~ ✅
7. **Rewrite matching engine** ← Phase 6 rewrite (multi-tier, all-combinations)
8. **Load CMS Rural + Non-Rural rates** ← Phase 7 update
9. **Expand CMS/OHA benchmark cascade** ← Phase 7 update
10. **Refactor analyze script to consume cleaned PHCC CSVs** ← integration fix
11. **Run end-to-end validation** → populate `output/`
12. **Enhance XLSX output** (Phase 9) — including Rural vs Non-Rural tab
13. **Business review of category ranges** (L-code policy decision)

---

## Acceptance Criteria
The project is ready for business review only when:
- ~~PHCC HCPCS anomalies are fully audited~~ ✅
- ~~requested ranges are flattened~~ ✅
- ~~modifiers are normalized and mapped~~ ✅
- ~~note-based rate rows are preserved instead of guessed~~ ✅
- ~~lower-than-current benchmark checks are applied consistently~~ ✅
- ~~unresolved rows are isolated in a review queue~~ ✅
- matching engine emits all meaningful comparisons (not just first hit)
- cross-modifier fallback produces reference rows when exact match is absent
- code-only fallback compares against all PHCC modifier variants when no modifier match exists
- CMS/OHA benchmark uses B1→B4 cascade with modifier fallback
- CMS benchmark includes BOTH Rural and Non-Rural rates
- Rural vs Non-Rural comparison sheet in output XLSX
- analyze script consumes cleaned CSVs (not raw files)
- XLSX output is executive-ready with formatting and frozen panes
- end-to-end run completes with validated output in `output/`
```

---

**Summary of changes in this PLAN.md rewrite:**

1. **Workspace layout** updated — scripts now in `PHCC/scripts/`
2. **Phase 6** rewritten with multi-tier matching engine (T1–T4 + NO_MATCH), cross-modifier fallback cascade, emit-all-combinations logic, detailed scenarios
3. **Phase 7** expanded — `load_cms()` now loads both `(NR)` and `(R)` columns; `lookup_benchmark()` returns both rates; benchmark status evaluated independently for Rural and Non-Rural
4. **Phase 8** gains new review triggers for Rural/NR split status and cross-modifier mismatches
5. **Phase 9** adds "Rural vs Non-Rural" XLSX tab with side-by-side CMS NR/R comparison, conditional formatting for split status
6. **Next Steps** and **Acceptance Criteria** updated with the new requirements

To answer your direct question: **yes, currently only Non-Rural is used.** The fix is to load both columns and surface them in the output. Please enable editing tools so I can apply these changes to the file, or copy the markdown block above into [PLAN.md](.github/PLAN.md). ---

**Summary of changes in this PLAN.md rewrite:**

1. **Workspace layout** updated — scripts now in `PHCC/scripts/`
2. **Phase 6** rewritten with multi-tier matching engine (T1–T4 + NO_MATCH), cross-modifier fallback cascade, emit-all-combinations logic, detailed scenarios
3. **Phase 7** expanded — `load_cms()` now loads both `(NR)` and `(R)` columns; `lookup_benchmark()` returns both rates; benchmark status evaluated independently for Rural and Non-Rural
4. **Phase 8** gains new review triggers for Rural/NR split status and cross-modifier mismatches
5. **Phase 9** adds "Rural vs Non-Rural" XLSX tab with side-by-side CMS NR/R comparison, conditional formatting for split status
6. **Next Steps** and **Acceptance Criteria** updated with the new requirements

To answer your direct question: **yes, currently only Non-Rural is used.** The fix is to load both columns and surface them in the output. Please enable editing tools so I can apply these changes to the file, or copy the markdown block above into [PLAN.md](.github/PLAN.md). 

