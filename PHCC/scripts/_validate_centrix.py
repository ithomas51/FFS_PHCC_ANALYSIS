#!/usr/bin/env python3
"""
_validate_centrix.py -- Validate centrix_rate_analysis.xlsx output
==================================================================
Reads output XLSX + source CSVs, checks expected vs actual on every dimension.
"""
import re, math, sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT   = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output" / "centrix_rate_analysis.xlsx"

# =====================================================================
# Known ground-truth from census
# =====================================================================
EXPECTED_UNIVERSE   = 2347
EXPECTED_CENTRIX    = 2343
EXPECTED_PHCC       = 300
EXPECTED_BOTH       = 296
EXPECTED_CX_ONLY    = 2047
EXPECTED_PHCC_ONLY  = 4
PHCC_ONLY_CODES     = {"E1019", "E2223", "E2300", "E2618"}

PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK] {label}")
    else:
        FAIL += 1
        print(f"  [X]  {label}  -- {detail}")


def validate_tab(df, tab_name):
    print(f"\n{'='*60}")
    print(f"TAB: {tab_name}")
    print(f"{'='*60}")

    # 1. Row count
    check("Row count = Universe",
          len(df) == EXPECTED_UNIVERSE,
          f"got {len(df)}, expected {EXPECTED_UNIVERSE}")

    # 2. No duplicate HCPC
    dupes = df["HCPC"].duplicated().sum()
    check("No duplicate HCPC codes",
          dupes == 0,
          f"found {dupes} duplicates")

    # 3. Source classification
    src = df["Source"].value_counts().to_dict()
    both_ct    = src.get("BOTH", 0)
    cx_only_ct = src.get("CENTRIX_ONLY", 0)
    ph_only_ct = src.get("PHCC_ONLY", 0)

    check(f"BOTH count = {EXPECTED_BOTH}",
          both_ct == EXPECTED_BOTH,
          f"got {both_ct}")
    check(f"CENTRIX_ONLY count = {EXPECTED_CX_ONLY}",
          cx_only_ct == EXPECTED_CX_ONLY,
          f"got {cx_only_ct}")
    check(f"PHCC_ONLY count = {EXPECTED_PHCC_ONLY}",
          ph_only_ct == EXPECTED_PHCC_ONLY,
          f"got {ph_only_ct}")
    check("Source totals = Universe",
          both_ct + cx_only_ct + ph_only_ct == EXPECTED_UNIVERSE,
          f"sum={both_ct + cx_only_ct + ph_only_ct}")

    # 4. PHCC_ONLY codes match expected set
    phcc_only_actual = set(df[df["Source"] == "PHCC_ONLY"]["HCPC"].tolist())
    check("PHCC_ONLY codes match expected",
          phcc_only_actual == PHCC_ONLY_CODES,
          f"got {phcc_only_actual}")

    # 5. PHCC_ONLY rows have blank Centrix rates
    phcc_only_rows = df[df["Source"] == "PHCC_ONLY"]
    cx_nu_blank = phcc_only_rows["Centrix NU"].isna().all()
    cx_rr_blank = phcc_only_rows["Centrix RR"].isna().all()
    check("PHCC_ONLY -> Centrix NU blank", cx_nu_blank)
    check("PHCC_ONLY -> Centrix RR blank", cx_rr_blank)

    # 6. CENTRIX_ONLY rows have blank PHCC rates
    cx_only_rows = df[df["Source"] == "CENTRIX_ONLY"]
    # Find PHCC column (dynamic name)
    phcc_nu_col = [c for c in df.columns if c.startswith("PHCC") and c.endswith("NU")
                   and "Note" not in c][0]
    phcc_rr_col = [c for c in df.columns if c.startswith("PHCC") and c.endswith("RR")
                   and "Note" not in c][0]
    ph_nu_blank = cx_only_rows[phcc_nu_col].isna().all()
    ph_rr_blank = cx_only_rows[phcc_rr_col].isna().all()
    check("CENTRIX_ONLY -> PHCC NU blank", ph_nu_blank)
    check("CENTRIX_ONLY -> PHCC RR blank", ph_rr_blank)

    # 7. Centrix NU population (should be most of the 2343 codes minus
    #    the ~280 MSRP codes that are non-numeric -> at least 1800 numeric)
    cx_nu_pop = df["Centrix NU"].notna().sum()
    check(f"Centrix NU populated > 1800 (got {cx_nu_pop})",
          cx_nu_pop > 1800)

    # 8. Centrix RR population (census: 415 codes have RR)
    cx_rr_pop = df["Centrix RR"].notna().sum()
    check(f"Centrix RR populated > 350 (got {cx_rr_pop})",
          cx_rr_pop > 350)

    # 9. Delta correctness: spot-check 10 BOTH codes where both are numeric
    both_rows = df[(df["Source"] == "BOTH")
                   & df["Centrix NU"].notna()
                   & df[phcc_nu_col].notna()]
    sample = both_rows.head(10)
    delta_ok = 0
    for _, row in sample.iterrows():
        expected_d = row["Centrix NU"] - row[phcc_nu_col]
        actual_d   = row["Delta NU"]
        if pd.notna(actual_d) and abs(actual_d - expected_d) < 0.015:
            delta_ok += 1
    check(f"Delta NU spot-check {delta_ok}/10 correct",
          delta_ok >= 9,
          f"only {delta_ok}/10")

    # 10. Flag logic: NEW CODE only on CENTRIX_ONLY
    new_code_rows = df[df["Flag NU"].fillna("").str.contains("NEW CODE")]
    new_code_in_both = new_code_rows[new_code_rows["Source"] == "BOTH"]
    check("NEW CODE flag not on BOTH rows",
          len(new_code_in_both) == 0,
          f"found {len(new_code_in_both)} BOTH rows with NEW CODE")

    # 11. PHCC ONLY flag only on PHCC_ONLY source
    phcc_only_flag = df[df["Flag NU"].fillna("").str.contains("PHCC ONLY")]
    phcc_only_wrong = phcc_only_flag[phcc_only_flag["Source"] != "PHCC_ONLY"]
    check("PHCC ONLY flag only on PHCC_ONLY source",
          len(phcc_only_wrong) == 0,
          f"found {len(phcc_only_wrong)} wrong")

    # 12. NON-NUMERIC PROPOSED flag check: these should have note text
    nn_prop = df[df["Flag NU"].fillna("") == "NON-NUMERIC PROPOSED"]
    if len(nn_prop) > 0:
        has_note = nn_prop["Centrix NU Note"].fillna("").str.len() > 0
        check(f"NON-NUMERIC PROPOSED have note text ({has_note.sum()}/{len(nn_prop)})",
              has_note.sum() == len(nn_prop))
    else:
        check("NON-NUMERIC PROPOSED flag count > 0 (MSRP codes exist)",
              False, "no NON-NUMERIC PROPOSED flags found")

    # 13. Flag distribution summary
    print(f"\n  Flag NU distribution:")
    for flag, cnt in df["Flag NU"].fillna("(blank)").value_counts().items():
        print(f"    {flag}: {cnt}")
    print(f"\n  Flag RR distribution:")
    for flag, cnt in df["Flag RR"].fillna("(blank)").value_counts().items():
        print(f"    {flag}: {cnt}")


def main():
    if not OUTPUT.exists():
        print(f"ERROR: {OUTPUT} not found. Run centrix_rate_analysis.py first.")
        sys.exit(1)

    print(f"Reading {OUTPUT} ...")

    # Check tabs exist
    xl = pd.ExcelFile(OUTPUT)
    sheets = xl.sheet_names
    print(f"Tabs found: {sheets}")

    check("Summary tab exists", "Summary" in sheets)
    check("vs Managed tab exists", "vs Managed" in sheets)
    check("vs Commercial tab exists", "vs Commercial" in sheets)

    for tab in ["vs Managed", "vs Commercial"]:
        if tab in sheets:
            df = pd.read_excel(OUTPUT, sheet_name=tab)
            validate_tab(df, tab)

    print(f"\n{'='*60}")
    print(f"TOTAL: {PASS} PASS, {FAIL} FAIL")
    if FAIL == 0:
        print("[OK] ALL VALIDATIONS PASSED")
    else:
        print(f"[X] {FAIL} FAILURES DETECTED")


if __name__ == "__main__":
    main()
