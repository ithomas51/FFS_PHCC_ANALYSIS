

Let me investigate the Rural vs Non-Rural rate columns across the data files to understand what's available and how comparisons currently work.    

Read [](file:///c%3A/Users/ithom/Downloads/FFS_PHCC_ANALYSIS/PHCC/data/Contract/PHCC_OR_CONTRACTED.csv#1-1), lines 1 to 10

Read [](file:///c%3A/Users/ithom/Downloads/FFS_PHCC_ANALYSIS/PHCC/data/cms/CMS_2026_Q1_OR.csv#1-1), lines 1 to 15

Read [](file:///c%3A/Users/ithom/Downloads/FFS_PHCC_ANALYSIS/PHCC/data/cms/CMS_2026_Q1_WA.csv#1-1), lines 1 to 15

Read [](file:///c%3A/Users/ithom/Downloads/FFS_PHCC_ANALYSIS/PHCC/data/INTEGRA_PHP_FFS/Integra_PHP_CARVEOUTS_COMMERCIAL.csv#1-1), lines 1 to 10

Read [](file:///c%3A/Users/ithom/Downloads/FFS_PHCC_ANALYSIS/PHCC/data/INTEGRA_PHP_FFS/Integra_PHP_CARVEOUTS_MEDICARE.csv#1-1), lines 1 to 10

Read [](file:///c%3A/Users/ithom/Downloads/FFS_PHCC_ANALYSIS/PHCC/data/cms/OHA_FFS_09_2025_RAW.csv#1-1), lines 1 to 10

Read [](file:///c%3A/Users/ithom/Downloads/FFS_PHCC_ANALYSIS/PHCC/data/INTEGRA_PHP_FFS/INTEGRA_PHP_CARVEOUTS_MEDICAID.csv#1-1), lines 1 to 10

Now let me see how the analyze script currently handles Rural vs Non-Rural CMS rates.  

Searched for regex `rural|Rural|NR|_R\b|\(R\)|\(NR\)` (`**/PHCC/scripts/analyze_fee_schedules.py`), 5 results

Searched for regex `rural|Rural|NR|_R\b|\(R\)|\(NR\)` (`**/PHCC/analyze_fee_schedules.py`), no results

Read [](file:///c%3A/Users/ithom/Downloads/FFS_PHCC_ANALYSIS/PHCC/scripts/analyze_fee_schedules.py#310-310), lines 310 to 360

Read [](file:///c%3A/Users/ithom/Downloads/FFS_PHCC_ANALYSIS/PHCC/scripts/analyze_fee_schedules.py#740-740), lines 740 to 770

Now let me check how `lookup_benchmark` uses the CMS lookup — it only loads `(NR)` column: 

Read [](file:///c%3A/Users/ithom/Downloads/FFS_PHCC_ANALYSIS/PHCC/scripts/analyze_fee_schedules.py#555-555), lines 555 to 600

Now let me check what the CMS data looks like for Rural rates — specifically, are there many codes where `(R)` has a different (non-zero) rate: 

Searched for regex `,(?!0$)[0-9]+\.?[0-9]*$` (`**/PHCC/data/cms/CMS_2026_Q1_OR.csv`), no results

Searched for regex `OR \(R\)` (`**/PHCC/data/cms/CMS_2026_Q1_OR.csv`), 1 result

Let me see some rows where Rural rate is non-zero and differs from Non-Rural: 

Read [](file:///c%3A/Users/ithom/Downloads/FFS_PHCC_ANALYSIS/PHCC/data/cms/CMS_2026_Q1_OR.csv#1-1), lines 1 to 30

Now let me understand the full rate column picture across all data sources. Let me also check how many CMS rows have non-zero Rural rates: 

Searched for regex `,[1-9][0-9]*\.?[0-9]*,[A-Z]` (`**/PHCC/data/cms/CMS_2026_Q1_OR.csv`), 30 results

Good. Now I have a complete picture. Here's the analysis:

---

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
- For codes where NR = 0 but Rural > 0 (e.g., `A4636|NU,KE` where NR = 0, R = 