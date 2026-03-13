# Centrix Care OR — Fee Schedule Analysis Methodology

## 1. Objective

Compare **Centrix Care OR** proposed rates against:
- **PHCC OR Contracted** current rates (both Managed and Commercial rate columns)
- **CMS 2026 Q1 OR** Medicare fee schedule (benchmark floor)
- **OHA FFS Medicaid** Oregon Medicaid reimbursement (Medicaid reference)

No WA (Washington) comparison — Centrix contract covers Oregon only.

---

## 2. Data Sources

### 2.1 Centrix Care OR (Proposed)
| Property | Detail |
|----------|--------|
| File | `data/CENTRIX/Centrix_Care_OR.csv` |
| Headers | `HCPC, MOD1, MOD2, MOD3, MOD4, CAT, TYPE, DESCRIPTION, SERVICE CODE, UOM, RATE, PROVIDE SERVICE` |
| Rows | ~1,774 data rows |
| Unique codes | ~1,100 HCPC codes |
| Modifiers | NU (~1,220 rows), RR (~400 rows), SQ (~40), blank (~60), others (~54) |
| Rate format | Dollar amounts (`$0.13`) or text formulas (`MSRP - 30%`) |
| Numeric rates | ~62% of rows have parseable dollar amounts |
| Text rates | ~37% are `MSRP - 30%` (non-numeric, flagged separately) |

### 2.2 PHCC OR Contracted (Current)
| Property | Detail |
|----------|--------|
| File | `data/cleaned/PHCC_OR_CONTRACTED_CLEAN.csv` |
| Key columns | `hcpcs_normalised, modifier_normalised` |
| Rate columns (Managed) | `Managed Rental Rate_numeric` (RR), `Managed Purchase Rate_numeric` (NU) |
| Rate columns (Commercial) | `Commercial Rental Rate_numeric` (RR), `Commercial Purchase Rate_numeric` (NU) |
| Note types | `NUMERIC`, `PERCENT_OF_MEDICARE_ALLOWABLE`, `PERCENT_OF_RETAIL` |
| Prerequisite | Requires `clean_phcc_files.py` to have been run |

### 2.3 CMS 2026 Q1 OR (Benchmark)
| Property | Detail |
|----------|--------|
| File | `data/cms/CMS_2026_Q1_OR.csv` |
| Key columns | `HCPCS, Mod, OR (NR), OR (R)` |
| Usage | Non-Rural `OR (NR)` as benchmark floor |
| Cascade | Exact modifier match -> blank modifier fallback |

### 2.4 OHA Medicaid (Reference)
| Property | Detail |
|----------|--------|
| File | `data/cms/OHA_FFS_09_2025_RAW.csv` |
| Key columns | `Procedure Code, Mod1, Price` |
| Usage | Medicaid reference rate |

### 2.5 HCPCS Descriptions
| Property | Detail |
|----------|--------|
| File | `data/cms/2026_CMS_HCPCS.csv` |
| Key columns | `HCPC, SHORT DESCRIPTION` |

---

## 3. Code Universe Construction

```
Universe = UNION(Centrix HCPC codes, PHCC OR_CONTRACTED codes)
```

- All valid HCPCS codes (pattern `^[A-Z][0-9]{4}$`) from both sources
- One row per unique code per output tab
- Source classification per code:
  - **BOTH** — code exists in Centrix AND PHCC
  - **CENTRIX_ONLY** — code in Centrix only (new code being proposed)
  - **PHCC_ONLY** — code in current PHCC contract but not in Centrix proposal

---

## 4. Modifier-to-Slot Mapping

Each code has two independent rate slots: **NU** (purchase) and **RR** (rental).

### Centrix
| MOD1 value | Slot assigned |
|-----------|---------------|
| `RR` | RR |
| `NU`, blank, `SQ`, all others | NU |

### PHCC OR Contracted
| modifier_normalised | Managed tab | Commercial tab |
|--------------------|-------------|----------------|
| `NU` | `Managed Purchase Rate_numeric` | `Commercial Purchase Rate_numeric` |
| `RR` | `Managed Rental Rate_numeric` | `Commercial Rental Rate_numeric` |

### CMS OR
| Mod | NU slot | RR slot |
|-----|---------|---------|
| `NU` | `OR (NR)` | — |
| `RR` | — | `OR (NR)` |
| blank | fallback for both | fallback for both |

### OHA
| Mod1 | Slot |
|------|------|
| `RR` | RR |
| blank, `NU`, others | NU |

---

## 5. PHCC Rate Resolution

### 5.1 PERCENT_OF_MEDICARE_ALLOWABLE
When PHCC note_type = `PERCENT_OF_MEDICARE_ALLOWABLE`:
```
resolved_rate = CMS_OR_NR_rate * (1 - percentage / 100)
```
Example: "Medicare Allowable less 20%" with CMS rate $10.00 → $8.00

### 5.2 PERCENT_OF_RETAIL
Cannot be resolved (no retail price source). Left as non-numeric.

### 5.3 NUMERIC
Used directly as the current rate.

---

## 6. Output Structure

### File: `output/centrix_rate_analysis.xlsx`

### Tabs
| Tab | Purpose |
|-----|---------|
| **Summary** | Universe statistics, flag distributions |
| **vs Managed** | Centrix proposed vs PHCC Managed rates + CMS + OHA |
| **vs Commercial** | Centrix proposed vs PHCC Commercial rates + CMS + OHA |

### Columns per analysis tab (22 columns)

| # | Column | Source | Format |
|---|--------|--------|--------|
| 1 | HCPC | Universe | Text |
| 2 | Description | CMS HCPCS ref | Text |
| 3 | Source | Classification | Text |
| 4 | Centrix CAT | Centrix | Text |
| 5 | Centrix TYPE | Centrix | Text |
| 6 | Centrix NU | Proposed purchase | Currency |
| 7 | Centrix RR | Proposed rental | Currency |
| 8 | Centrix NU Note | Non-numeric text | Text |
| 9 | Centrix RR Note | Non-numeric text | Text |
| 10 | PHCC Current NU | Current purchase | Currency |
| 11 | PHCC Current RR | Current rental | Currency |
| 12 | PHCC Note NU | Note type | Text |
| 13 | PHCC Note RR | Note type | Text |
| 14 | CMS OR NU | Benchmark purchase | Currency |
| 15 | CMS OR RR | Benchmark rental | Currency |
| 16 | OHA NU | Medicaid purchase | Currency |
| 17 | OHA RR | Medicaid rental | Currency |
| 18 | Delta NU | Centrix NU - PHCC NU | Currency |
| 19 | Delta RR | Centrix RR - PHCC RR | Currency |
| 20 | Delta% NU | (Delta / PHCC) * 100 | Percent |
| 21 | Delta% RR | (Delta / PHCC) * 100 | Percent |
| 22 | Flag NU | Decision classification | Text |
| 23 | Flag RR | Decision classification | Text |

---

## 7. Delta Calculation

```
Delta NU = Centrix_NU - PHCC_Current_NU
Delta% NU = (Delta NU / PHCC_Current_NU) * 100

Delta RR = Centrix_RR - PHCC_Current_RR
Delta% RR = (Delta RR / PHCC_Current_RR) * 100
```

Both values are blank when either side is non-numeric or missing.

---

## 8. Decision Flags

### 8.1 Primary Flags (mutually exclusive, per NU/RR slot)

| Priority | Flag | Condition |
|----------|------|-----------|
| 1 | `PHCC ONLY` | Code in PHCC but not Centrix, and current rate exists |
| 2 | `NON-NUMERIC PROPOSED` | Centrix rate is text (e.g., "MSRP - 30%") |
| 3 | `NEW CODE` | Code in Centrix but not PHCC |
| 4 | `NON-NUMERIC CURRENT` | PHCC rate is text (can't compare) |
| 5 | `NO CHANGE` | abs(Delta%) <= 1% |
| 6 | `RATE INCREASE` | Centrix > PHCC (Delta > 0, beyond tolerance) |
| 7 | `BELOW CURRENT` | Centrix < PHCC but Centrix >= CMS |
| 8 | `BELOW CMS FLOOR` | Centrix < PHCC and Centrix < CMS |

### 8.2 Systemic Flag (appended)

| Flag | Condition |
|------|-----------|
| `PHCC BELOW CMS` | Current PHCC rate < CMS benchmark (appended with `\|`) |

---

## 9. Validation Criteria

| Check | Expected |
|-------|----------|
| Row count per tab | = Universe size |
| No duplicate HCPC codes per tab | 0 duplicates |
| Source classification totals | BOTH + CENTRIX_ONLY + PHCC_ONLY = Universe |
| Delta correctness | spot-check 10 codes per tab |
| Flag logic consistency | spot-check 10 codes per tab |
| CENTRIX_ONLY codes have blank PHCC | Confirmed |
| PHCC_ONLY codes have blank Centrix | Confirmed |

---

## 10. Limitations

1. **MSRP - 30%** rates cannot be resolved to numeric values (no MSRP source). These are flagged as `NON-NUMERIC PROPOSED`.
2. **PERCENT_OF_RETAIL** PHCC rates cannot be resolved. Flagged as `NON-NUMERIC CURRENT`.
3. **No WA comparison** — Centrix contract is Oregon-only.
4. **Single Centrix rate** — One rate per code/modifier applies to both Managed and Commercial comparison tabs (same proposed rate, different current baselines).
5. Centrix modifiers other than NU/RR (SQ, HB, TF, EY, KF, SC) are mapped to the **NU slot** since they represent purchase-type transactions.
