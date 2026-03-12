# Plan: Delete and Rewrite analyze_fee_schedules.py

## Status: READY FOR APPROVAL — comprehensive plan below

## Approach
Delete old v2 script (1,047 lines) and write brand new script from scratch.
Incorporates all CONSIDERATIONS.MD specs (multi-tier matching, Rural/NR, B1-B4 cascade).

## Confirmed Decisions
1. Rural vs Non-Rural: NR primary, R as secondary reference column
2. OR_PARTICIPATING: Loaded as separate comparison target (3 schedules total)
3. OR_CONTRACTED rate mapping: Commercial/ASO → Commercial cols, Medicare/Medicaid → Managed cols
4. Cleaned files: Load from data/cleaned/ only
5. Multi-tier matching: T1-T4 per CONSIDERATIONS.MD
6. CMS/OHA benchmark cascade: B1-B4 per CONSIDERATIONS.MD
7. 9-tab XLSX output with Rural vs Non-Rural tab

## PLAN.md needs updating
The full comprehensive plan has been presented to user. PLAN.md file needs to be replaced
with the new version (too large for current editing session — will update when editing tools available).

## New Script Architecture (~1,000 lines, 7 sections)
1. Pure Functions (~80 lines): normalize_hcpcs, validate_hcpcs, safe_float, classify_pricing_note, norm_mod
2. Loaders (~200 lines): load_cleaned_phcc, load_integra, load_cms (NR+R), load_oha, load_hcpcs_descriptions
3. PHCC Lookup Builder (~30 lines): build_phcc_lookup
4. Multi-tier Matching Engine (~150 lines): match_all_tiers → list[dict] (T1-T4)
5. Benchmark Cascade Engine (~80 lines): lookup_benchmark_cascade (B1-B4, NR+R)
6. Main Pipeline (~200 lines): run_analysis
7. XLSX Output Writer (~300 lines): 9 tabs with formatting

## XLSX Tab Structure
1. Executive Summary — payer × state × schedule matrix (primary only)
2. All Comparisons — full master (primary matches)
3. Reference Matches — T2-T4 supplemental context
4. Lower Than Current — filtered LOWER
5. Below Benchmark — filtered BELOW_BENCHMARK (NR primary)
6. Rural vs Non-Rural — Medicare side-by-side NR/R comparison
7. Review Queue — flagged rows
8. Audit Trail — HCPCS audit + range expansion
9. Data Sources — file inventory + processing date

## Output Column Count: ~55 columns
Including new: match_tier, is_primary_match, is_reference_match, cross_mod_used,
all_phcc_mods_available, benchmark_match_tier, benchmark_mod_used, benchmark_mod_mismatch,
cms_benchmark_nr, cms_benchmark_r, benchmark_status_nr, benchmark_status_r,
delta_vs_cms_nr/r, pct_delta_vs_cms_nr/r, oha_benchmark, oha_benchmark_status,
delta_vs_oha, pct_delta_vs_oha, current_rate_col_used

## Implementation Steps
1. Delete old script
2. Write new script (7 sections)
3. Run clean_phcc_files.py (prerequisite)
4. Run new analyze script
5. Validate output (spot-check known codes: A4595, A7005, A4604)
6. Update SKILL.md and PLAN.md
