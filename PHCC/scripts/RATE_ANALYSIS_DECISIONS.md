# INTEGRA PHP FFS — Executive Rate Analysis
## Decision Tree & Design Choices

### Data Validation Findings
| Finding | Detail |
|---------|--------|
| OR_CONTRACTED vs OR_PARTICIPATING | **0 HCPCS overlap** — completely different code sets |
| OR_P vs WA_P (128 overlapping keys) | **100% identical Purchase Rates** where codes overlap |
| OR_C vs WA_P | 258 codes overlap — different column structure (Managed/Commercial vs unified) |
| Integra Commercial vs ASO | Only 408/1071 identical rates — **treat separately** |
| Integra Medicare vs Medicaid | 545/1071 identical — **substantially different** |
| "Prevailing State Rates" entries | Common in Commercial/ASO, less in Medicare/Medicaid |

### Decision: One Tab Per Integra Payer
**Why:** Rates differ significantly across all 4 Integra contract types. Combining them
would obscure per-payer negotiation leverage.

**Tabs:**
1. **Executive Summary** — Overall rate positioning at a glance
2. **Commercial** — Integra proposed Commercial vs PHCC current vs CMS NR/R
3. **ASO** — Integra proposed ASO vs PHCC current vs CMS NR/R
4. **Medicare** — Integra proposed Medicare vs PHCC current vs CMS NR/R
5. **Medicaid** — Integra proposed Medicaid vs PHCC current vs CMS NR/R (OHA benchmark)

### Decision: Slim Column Set (12 cols vs 35+ in main script)
| Column | Purpose |
|--------|---------|
| HCPCS | Code identifier |
| Mod | Modifier |
| Description | From CMS HCPCS reference |
| Proposed Rate | Integra's ask |
| PHCC Current | Our current contracted rate |
| Δ Proposed vs PHCC | Dollar difference |
| CMS NR Rate | Medicare Non-Rural benchmark |
| CMS Rural Rate | Medicare Rural benchmark |
| PHCC vs CMS NR | +/- status (Above/Below/Equal) |
| Proposed vs CMS NR | +/- status |
| Flag | Highlight category for exec action |
| State / Schedule | Context |

### Decision: Highlight Logic (3 flags, color-coded)
| Flag | Color | Meaning | Executive Action |
|------|-------|---------|-----------------|
| **PHCC ABOVE PROPOSED** | 🟢 Green | Our current rate > Integra's offer → rate cut | Review if acceptable |
| **PROPOSED BELOW CMS** | 🔴 Red | Integra proposes below Medicare floor | Negotiate UP |
| **PHCC BELOW CMS** | 🟡 Yellow | Our current rate already below Medicare | Systemic issue — adjust contract |

### Decision: PHCC Schedule Matching Strategy
- **OR state**: Use OR_CONTRACTED (Managed cols for Medicare/Medicaid, Commercial cols for Commercial/ASO) + OR_PARTICIPATING (unified rate cols) — distinct code sets, no dedup needed
- **WA state**: Use WA_PARTICIPATING only (unified rate cols)
- Consume **cleaned** CSVs from `clean_phcc_files.py` (OCR artifacts already fixed)

### Decision: Non-Numeric Rates
- "Prevailing State Rates", "Retail less X%", "Non-Billable" → shown as-is in a Note column
- Numeric comparisons only where both rates parse to floats
- Flag = "NOT_COMPARABLE" when either rate is non-numeric

### Output File
`PHCC/output/integra_rate_analysis.xlsx` — separate from main comparison workbook
