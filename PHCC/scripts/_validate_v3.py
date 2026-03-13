"""
Validation script for unified_code_analysis.py (v3)
====================================================
Checks: universe counts, source classification, delta correctness,
flag logic, matching percentages, no duplicate codes.
"""
import math, sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "output" / "unified_code_analysis.xlsx"

if not XLSX.exists():
    print(f"ERROR: {XLSX} not found. Run unified_code_analysis.py first.")
    sys.exit(1)

print(f"Validating: {XLSX}\n")
PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    status = "PASS" if condition else "FAIL"
    if not condition:
        FAIL += 1
    else:
        PASS += 1
    print(f"  [{status}] {label}" + (f"  -- {detail}" if detail else ""))

# ── Load all tabs ──
xls = pd.ExcelFile(XLSX)
tabs = xls.sheet_names
print(f"Tabs found: {tabs}")
check("Has Summary tab", "Summary" in tabs)
check("Has 4 payer tabs", all(p in tabs for p in ["Commercial", "ASO", "Medicare", "Medicaid"]))
print()

# ── Per-payer checks ──
for payer in ["Commercial", "ASO", "Medicare", "Medicaid"]:
    df = pd.read_excel(XLSX, sheet_name=payer)
    print(f"=== {payer} ===")
    print(f"  Shape: {df.shape}")

    # 1. Universe count
    check(f"Row count = 1167", len(df) == 1167, f"got {len(df)}")

    # 2. No duplicate HCPCS
    dupes = df["HCPCS"].duplicated().sum()
    check("No duplicate HCPCS", dupes == 0, f"{dupes} duplicates")

    # 3. Source classification
    src_counts = df["Source"].value_counts().to_dict()
    check("BOTH = 312", src_counts.get("BOTH", 0) == 312,
          f"got {src_counts.get('BOTH', 0)}")
    check("INTEGRA_ONLY = 676", src_counts.get("INTEGRA_ONLY", 0) == 676,
          f"got {src_counts.get('INTEGRA_ONLY', 0)}")
    check("PHCC_ONLY = 179", src_counts.get("PHCC_ONLY", 0) == 179,
          f"got {src_counts.get('PHCC_ONLY', 0)}")

    # 4. Integra NU populated count (should be ~988 - some may have NaN rates)
    int_nu_pop = df["Integra NU"].notna().sum()
    int_rr_pop = df["Integra RR"].notna().sum()
    print(f"  Integra NU populated: {int_nu_pop}")
    print(f"  Integra RR populated: {int_rr_pop}")
    # Many Integra rates are text ("Prevailing State Rates", "Cost Invoice")
    # Numeric NU counts: Commercial~573, ASO~615, Medicare~595, Medicaid~640
    check("Integra NU > 500", int_nu_pop > 500, f"{int_nu_pop}")

    # 5. PHCC population
    phcc_nu_any = (df["OR Contract NU"].notna()
                   | df["OR Partic NU"].notna()
                   | df["WA Partic NU"].notna()).sum()
    phcc_rr_any = (df["OR Contract RR"].notna()
                   | df["OR Partic RR"].notna()
                   | df["WA Partic RR"].notna()).sum()
    print(f"  PHCC NU (any schedule): {phcc_nu_any}")
    print(f"  PHCC RR (any schedule): {phcc_rr_any}")
    check("PHCC NU any >= 300", phcc_nu_any >= 300, f"{phcc_nu_any}")

    # 6. CMS population
    cms_nu = df["CMS OR NU"].notna().sum() + df["CMS WA NU"].notna().sum()
    print(f"  CMS NU cells populated (OR+WA): {cms_nu}")

    # 7. Delta correctness — spot check 10 rows with both Integra and PHCC data
    has_both = df.dropna(subset=["Integra NU", "PHCC Source NU"])
    has_both = has_both[has_both["PHCC Source NU"] != ""]
    sample = has_both.head(10)
    delta_ok = 0
    for _, row in sample.iterrows():
        int_val = row["Integra NU"]
        src = row["PHCC Source NU"]
        if src == "OR_Contracted":
            phcc_val = row["OR Contract NU"]
        elif src == "OR_Participating":
            phcc_val = row["OR Partic NU"]
        else:
            phcc_val = row["WA Partic NU"]
        expected_delta = int_val - phcc_val if pd.notna(phcc_val) else None
        actual_delta = row.get("Δ NU")
        if expected_delta is not None and pd.notna(actual_delta):
            if abs(expected_delta - actual_delta) < 0.005:
                delta_ok += 1
            else:
                print(f"    DELTA MISMATCH: {row['HCPCS']} expected={expected_delta:.4f} got={actual_delta:.4f}")
        elif expected_delta is None and pd.isna(actual_delta):
            delta_ok += 1
    check(f"Delta NU correct ({delta_ok}/{len(sample)})", delta_ok == len(sample))

    # 8. Flag logic spot check
    flag_ok = 0
    for _, row in sample.iterrows():
        flag = row.get("Flag NU", "")
        d_pct = row.get("Δ% NU")
        if pd.notna(d_pct):
            if abs(d_pct) <= 1.0:
                ok = "NO CHANGE" in str(flag)
            elif d_pct > 0:
                ok = "RATE INCREASE" in str(flag)
            else:
                ok = ("BELOW CURRENT" in str(flag) or "BELOW CMS FLOOR" in str(flag))
            if ok:
                flag_ok += 1
            else:
                print(f"    FLAG MISMATCH: {row['HCPCS']} D%={d_pct:.1f} flag={flag}")
        else:
            flag_ok += 1  # Can't verify without delta
    check(f"Flag NU logic correct ({flag_ok}/{len(sample)})", flag_ok == len(sample))

    # 9. PHCC_ONLY rows should have blank Integra
    phcc_only = df[df["Source"] == "PHCC_ONLY"]
    int_blank = phcc_only["Integra NU"].isna().all() and phcc_only["Integra RR"].isna().all()
    check("PHCC_ONLY -> Integra rates blank", int_blank)

    # 10. INTEGRA_ONLY rows should have blank PHCC
    int_only = df[df["Source"] == "INTEGRA_ONLY"]
    phcc_blank = (int_only["OR Contract NU"].isna().all()
                  and int_only["OR Partic NU"].isna().all()
                  and int_only["WA Partic NU"].isna().all())
    check("INTEGRA_ONLY -> PHCC NU rates blank", phcc_blank)

    # 11. Flag distribution
    print(f"\n  NU Flag distribution:")
    flag_dist = df["Flag NU"].fillna("(blank)").value_counts()
    for f, c in flag_dist.items():
        print(f"    {f}: {c}")
    print(f"  RR Flag distribution:")
    flag_dist_rr = df["Flag RR"].fillna("(blank)").value_counts()
    for f, c in flag_dist_rr.items():
        print(f"    {f}: {c}")
    print()

# ── Final summary ──
print("=" * 50)
print(f"TOTAL: {PASS} PASS, {FAIL} FAIL")
if FAIL == 0:
    print("[OK] ALL VALIDATIONS PASSED")
else:
    print("[X] SOME VALIDATIONS FAILED -- see details above")
