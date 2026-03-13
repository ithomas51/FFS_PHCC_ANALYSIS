# Unified Code-Centric Fee Schedule Analysis — Methodology & Design

## Version
v3 — Code-Centric Approach  
Date: 2025-01-XX  
Script: `scripts/unified_code_analysis.py`

---

## 1. Objective

Produce a **complete, code-by-code comparison** of Integra PHP FFS proposed rates
against PHCC current contract rates, with CMS (Medicare) and OHA (Medicaid) public
benchmark checks. Every unique HCPCS code from **every source** is represented.
NU (purchase) and RR (rental) rates are matched **independently** per code.

### Key Difference from v2

| Aspect | v2 (integra_rate_analysis_v2.py) | v3 (unified_code_analysis.py) |
|--------|------|------|
| Starting set | Integra codes only (988) | UNION of Integra + PHCC (1,167) |
| Row structure | One row per (code × modifier × schedule × state) | One row per code — NU and RR as separate columns |
| Missing data | Cross-modifier fallback, tiered matching (T1–T5) | Strict NU/RR lookup — blank if not found |
| PHCC codes not in Integra | Not shown | Shown as "PHCC_ONLY" |
| Output rows per payer | ~3,234 | 1,167 (exactly one per code) |

---

## 2. Data Sources

### 2.1 Integra PHP FFS (Proposed Rates)

| File | Payer | Rate Column |
|------|-------|-------------|
| Integra_PHP_CARVEOUTS_COMMERCIAL.csv | Commercial | `Commercial` |
| Integra_PHP_CARVEOUTS_ASO.csv | ASO | `ASO/Commercial` |
| Integra_PHP_CARVEOUTS_MEDICARE.csv | Medicare | `Medicare` |
| INTEGRA_PHP_CARVEOUTS_MEDICAID.csv | Medicaid | `Medicaid` |

- **1,078 rows** per file, **988 unique HCPCS codes** (same codes across all 4 files)
- Modifier distribution: 949 blank, 100 RR, 10 BO, 4 QG, 4 AW, 3 TW, 2 AU, 2 KF, 2 QF, 1 BA

**NU/RR classification rule for Integra:**
- `Mod 1 == "RR"` → **RR slot** (rental rate)
- All other modifiers (blank, AU, KF, etc.) → **NU slot** (purchase rate)
- Rationale: Integra files do not use the NU modifier explicitly. Blank-modifier rows
  represent the purchase/new rate. Only RR is explicitly flagged as rental.

### 2.2 PHCC Current Schedules (Cleaned)

Prerequisite: `python scripts/clean_phcc_files.py` must be run first.

| File | Schedule | Rows | Valid Codes | Rate Columns |
|------|----------|------|-------------|--------------|
| PHCC_OR_CONTRACTED_CLEAN.csv | OR Contracted | 330 | 300 | Managed Rental/Purchase, Commercial Rental/Purchase |
| PHCC_OR_PARTICIPATING_CLEAN.csv | OR Participating | 199 | 149 | Rental Rate, Purchase Rate |
| PHCC_WA_PARTICIPATING_CLEAN.csv | WA Participating | 530 | 460 | Rental Rate, Purchase Rate |

- **491 unique valid HCPCS codes** across all 3 schedules
- Modifier distribution: NU (886 rows), RR (155 rows), other (18 rows)

**NU/RR classification rule for PHCC:**
- `modifier_normalised == "NU"` → **NU slot** → use Purchase Rate column
- `modifier_normalised == "RR"` → **RR slot** → use Rental Rate column
- Other modifiers (QE, QG, etc.) → **NU slot** (treated as purchase variant)

**OR Contracted rate column selection (payer-dependent):**
- Commercial / ASO payers → `Commercial Purchase Rate` (NU), `Commercial Rental Rate` (RR)
- Medicare / Medicaid payers → `Managed Purchase Rate` (NU), `Managed Rental Rate` (RR)

**Non-numeric rate handling:**
- `PERCENT_OF_MEDICARE_ALLOWABLE` → Resolved: CMS_NR × (1 − X/100)
- `PERCENT_OF_RETAIL` → Cannot resolve (no retail price source) → left blank
- `QUOTE_REQUIRED`, `NON_BILLABLE`, `PER_TIME_UNIT`, `COST_INVOICE` → Left blank
- `UNPARSED_TEXT` → Left blank

### 2.3 CMS 2026 Q1 DMEPOS Fee Schedule (Medicare Benchmark)

| File | State | Columns |
|------|-------|---------|
| CMS_2026_Q1_OR.csv | Oregon | `OR (NR)`, `OR (R)` |
| CMS_2026_Q1_WA.csv | Washington | `WA (NR)`, `WA (R)` |

- **3,515 rows** per file, **2,106 unique codes**
- Modifier distribution: 1,416 blank, 956 RR, 585 NU, 526 UE, others

**CMS NU/RR lookup rule:**
For slot NU:
1. Try `code|NU` from CMS → Non-Rural rate
2. If not found or zero, try `code|blank` → Non-Rural rate
3. If not found → NaN

For slot RR:
1. Try `code|RR` from CMS → Non-Rural rate
2. If not found or zero, try `code|blank` → Non-Rural rate
3. If not found → NaN

**Note:** Non-Rural (NR) rate is the primary benchmark. Rural rates are not shown
in this version (most codes have Rural = 0 for DMEPOS).

### 2.4 OHA Medicaid Fee Schedule (Medicaid Benchmark)

| File | Columns |
|------|---------|
| OHA_FFS_09_2025_RAW.csv | `Procedure Code`, `Mod1`, `Price` |

- **5,829 rows**, **3,977 unique codes**
- Modifier distribution: 3,736 blank, 1,508 NU, 495 RR, others

**OHA NU/RR lookup rule:**
- `Mod1 == "NU"` or blank → **NU slot**
- `Mod1 == "RR"` → **RR slot**
- Other modifiers → **NU slot** (treated as purchase variant)

### 2.5 HCPCS Reference (Descriptions)

| File | Key Column | Description Column |
|------|-----------|-------------------|
| 2026_CMS_HCPCS.csv | `HCPC` | `SHORT DESCRIPTION` |

- **8,623 codes** with descriptions

---

## 3. Code Universe Construction

```
Universe = UNION(Integra HCPCS codes, PHCC valid HCPCS codes)
```

| Set | Count |
|-----|-------|
| Integra unique codes | 988 |
| PHCC unique valid codes | 491 |
| **UNION (total unique)** | **1,167** |
| Overlap (in both) | 312 |
| Integra only | 676 |
| PHCC only | 179 |

Every code in the universe gets exactly **one row** per payer tab.

---

## 4. Output Structure

### 4.1 File
`output/unified_code_analysis.xlsx`

### 4.2 Tabs
1. **Summary** — Matching statistics, methodology summary, flag distribution
2. **Commercial** — 1,167 rows, Integra Commercial vs PHCC vs CMS vs OHA
3. **ASO** — 1,167 rows, Integra ASO vs PHCC vs CMS vs OHA
4. **Medicare** — 1,167 rows, Integra Medicare vs PHCC vs CMS vs OHA
5. **Medicaid** — 1,167 rows, Integra Medicaid vs PHCC vs CMS vs OHA

### 4.3 Per-Payer Tab Columns

| # | Column | Description |
|---|--------|-------------|
| 1 | HCPCS | Code |
| 2 | Description | From HCPCS reference |
| 3 | Source | `BOTH`, `INTEGRA_ONLY`, or `PHCC_ONLY` |
| 4 | Integra NU | Proposed purchase rate |
| 5 | Integra RR | Proposed rental rate |
| 6 | Integra Note | Non-numeric note text (e.g., "Prevailing State Rates") |
| 7 | OR Contract NU | PHCC OR Contracted purchase rate |
| 8 | OR Contract RR | PHCC OR Contracted rental rate |
| 9 | OR Partic NU | PHCC OR Participating purchase rate |
| 10 | OR Partic RR | PHCC OR Participating rental rate |
| 11 | WA Partic NU | PHCC WA Participating purchase rate |
| 12 | WA Partic RR | PHCC WA Participating rental rate |
| 13 | CMS OR NU | CMS Oregon Non-Rural purchase rate |
| 14 | CMS OR RR | CMS Oregon Non-Rural rental rate |
| 15 | CMS WA NU | CMS Washington Non-Rural purchase rate |
| 16 | CMS WA RR | CMS Washington Non-Rural rental rate |
| 17 | OHA NU | OHA Medicaid purchase rate |
| 18 | OHA RR | OHA Medicaid rental rate |
| 19 | Δ NU | Integra NU − PHCC Primary NU |
| 20 | Δ RR | Integra RR − PHCC Primary RR |
| 21 | Δ% NU | Percentage delta for NU |
| 22 | Δ% RR | Percentage delta for RR |
| 23 | Flag NU | Decision flag for purchase rate |
| 24 | Flag RR | Decision flag for rental rate |
| 25 | PHCC Source NU | Which schedule used for NU comparison |
| 26 | PHCC Source RR | Which schedule used for RR comparison |

---

## 5. Delta Calculations

### 5.1 PHCC Primary Selection

For each code, the "primary" PHCC rate for comparison is selected in priority order:
1. **OR Contracted** (if rate exists)
2. **OR Participating** (if rate exists)
3. **WA Participating** (if rate exists)
4. Blank (no PHCC rate → no delta)

This priority is applied **independently** for NU and RR:
- `PHCC Primary NU` may come from OR Contracted
- `PHCC Primary RR` may come from WA Participating (different schedule)

### 5.2 Delta Formula

```
Δ NU = Integra_NU − PHCC_Primary_NU
Δ% NU = (Δ NU / PHCC_Primary_NU) × 100

Δ RR = Integra_RR − PHCC_Primary_RR
Δ% RR = (Δ RR / PHCC_Primary_RR) × 100
```

**Blank policy:** If either Integra or PHCC rate is blank (NaN), the delta is blank.
No imputation, no fallback. This is a departure from v2 which used cross-modifier
fallback matching.

---

## 6. Decision Tree (Flags)

Flags are computed **independently** for NU and RR. Each flag applies to one modifier slot.

### 6.1 Flag Logic

```
IF Integra rate is blank:
    → "" (no flag — nothing proposed)
ELIF code is PHCC_ONLY (no Integra proposal):
    → "PHCC ONLY" (informational)
ELIF PHCC Primary rate is blank:
    → "NEW CODE" (Integra proposes but no PHCC rate to compare)
    Note: could be PHCC code exists but rate is non-numeric → "PHCC NON-NUMERIC"
ELIF |Δ%| ≤ 1.0%:
    → "NO CHANGE"
ELIF Proposed > Current:
    → "RATE INCREASE"
ELIF Proposed < Current:
    IF CMS benchmark available AND Proposed ≥ CMS:
        → "BELOW CURRENT" (still above Medicare floor)
    ELIF CMS benchmark available AND Proposed < CMS:
        → "BELOW CMS FLOOR" (critical — below Medicare rate)
    ELSE (no CMS data):
        → "BELOW CURRENT"
```

### 6.2 Systemic Flag

Appended regardless of primary flag:
```
IF PHCC Current < CMS benchmark:
    → append " | PHCC BELOW CMS"
```

### 6.3 Flag Color Legend

| Flag | Meaning | Color |
|------|---------|-------|
| BELOW CMS FLOOR | Proposed below Medicare benchmark | Red |
| PHCC BELOW CMS | Current PHCC rate is below CMS | Orange |
| BELOW CURRENT | Proposed below current, above CMS | Yellow |
| RATE INCREASE | Proposed above current | Blue |
| NO CHANGE | Within ±1% tolerance | Green |
| NEW CODE | Code not in PHCC (Integra-only) | Gray |
| PHCC ONLY | Code not in Integra (PHCC-only) | Light gray |
| PHCC NON-NUMERIC | PHCC rate is text-based (can't compare) | Gray |

---

## 7. CMS Benchmark Selection

For the flag calculation, the CMS benchmark must correspond to the PHCC schedule used:

| PHCC Source | CMS Benchmark |
|-------------|---------------|
| OR Contracted | CMS Oregon (NR) |
| OR Participating | CMS Oregon (NR) |
| WA Participating | CMS Washington (NR) |

If no PHCC source is selected (INTEGRA_ONLY code), no CMS comparison is performed
for the flag. However, CMS rates are still shown in the output for reference.

---

## 8. Validation Criteria

The deliverable is not complete until:

1. **Universe count**: Exactly 1,167 unique HCPCS codes per payer tab
2. **Source classification**:
   - BOTH: 312 codes
   - INTEGRA_ONLY: 676 codes
   - PHCC_ONLY: 179 codes
3. **Matching percentages** (codes with non-blank rates):
   - Integra NU populated: should be close to 988 (all Integra codes have a rate)
   - PHCC NU populated: should reflect actual PHCC NU rows per schedule
   - CMS NU populated: check against CMS 585 NU-modifier rows
4. **Delta correctness**: Spot-check 10 codes per payer, verify Δ = Integra − PHCC
5. **Flag correctness**: Verify flag logic matches decision tree for sampled rows
6. **No duplicate codes**: Each HCPCS appears exactly once per payer tab

---

## 9. Limitations and Assumptions

1. **Integra NU = non-RR**: Since Integra does not use NU modifier explicitly,
   all non-RR Integra rows are treated as purchase rates. Codes with AU, KF, etc.
   modifiers have their rate placed in the NU column.

2. **PERCENT_OF_RETAIL unresolved**: PHCC rates expressed as "Retail less X%"
   cannot be resolved to dollar amounts without a retail price source.
   These appear as blank numerics in the output.

3. **Rural rates not shown**: CMS Rural rates exist but are mostly $0 for DMEPOS.
   Non-Rural is the operative benchmark.

4. **OR Contracted payer split**: OR Contracted has separate Commercial and Managed
   rate columns. Each payer tab uses the appropriate set. This means the same HCPCS
   code may show different PHCC rates across payer tabs for OR Contracted.

5. **CATEGORY_RANGE rows (3 in WA)**: L-code ranges (L0112–L2861, L3000–L4631,
   L8300–L8485) are kept as-is in PHCC cleaned data. Individual L-codes from Integra
   that fall within these ranges will NOT match in v3 (unlike v2 which had T5 range
   matching). This is intentional for the strict code-centric approach.

6. **Single PHCC rate per code**: If a code appears in multiple PHCC rows with
   the same modifier (e.g., from range expansion), only the last row's rate is used.
