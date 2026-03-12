"""Validate integra_rate_analysis_v2 output."""
import pandas as pd, math, numpy as np
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output" / "integra_rate_analysis_v2.xlsx"

print(f"Validating: {OUT}\n")

for sheet in ["Commercial", "ASO", "Medicare", "Medicaid"]:
    df = pd.read_excel(OUT, sheet_name=sheet, header=None)
    # Find the header row (contains "HCPCS")
    for i in range(len(df)):
        if "HCPCS" in df.iloc[i].values:
            header_row = i
            break
    else:
        print(f"  {sheet}: HEADER ROW NOT FOUND")
        continue
    df = pd.read_excel(OUT, sheet_name=sheet, header=header_row)
    print(f"{'='*60}")
    print(f"  {sheet}: {len(df)} rows")
    print(f"{'='*60}")

    # 1. Match distribution
    print(f"  Match tiers:")
    for tier, cnt in df["Match"].value_counts().items():
        print(f"    {tier:12s}: {cnt:5d}")

    # 2. Flag distribution
    print(f"  Flags:")
    flags = df["Flag"].fillna("")
    for kw in ["BELOW CMS FLOOR", "BELOW CURRENT", "RATE INCREASE",
               "NO CHANGE", "PHCC BELOW CMS", "NEW CODE", "REVIEW"]:
        cnt = flags.str.contains(kw, na=False, regex=False).sum()
        if cnt > 0:
            print(f"    {kw:25s}: {cnt:5d}")

    # 3. Medicare Allowable resolved
    if "PHCC Raw" in df.columns:
        resolved = df["PHCC Raw"].fillna("").str.contains("→", na=False)
        print(f"  Medicare Allowable resolved: {resolved.sum()}")

    # 4. Spot-check: T5_RANGE rows should have PHCC Current
    t5 = df[df["Match"] == "T5_RANGE"]
    t5_with_rate = t5["PHCC Current"].notna().sum()
    t5_nan_rate = t5["PHCC Current"].isna().sum()
    print(f"  T5_RANGE rows: {len(t5)} total, {t5_with_rate} with PHCC rate, {t5_nan_rate} NaN")

    # 5. Spot-check specific L-code (L3000 if exists)
    l3000 = df[df["HCPCS"] == "L3000"]
    if len(l3000) > 0:
        for _, r in l3000.iterrows():
            state = r.get("State", "?")
            proposed = r.get("Proposed Rate", "?")
            phcc_cur = r.get("PHCC Current", "?")
            cms_nr = r.get("CMS NR", "?")
            flag = r.get("Flag", "?")
            raw = r.get("PHCC Raw", "?")
            match = r.get("Match", "?")
            print(f"  L3000 [{state}]: proposed={proposed}, phcc_cur={phcc_cur}, "
                  f"cms_nr={cms_nr}, flag={flag}, match={match}, raw={raw}")

    # 6. Delta validation: spot-check first 5 matched rows
    matched = df[(df["Match"] != "NO_MATCH") & df["Proposed Rate"].notna() & df["PHCC Current"].notna()]
    print(f"  Delta spot-check (first 5 matched):")
    for _, r in matched.head(5).iterrows():
        p = r["Proposed Rate"]
        c = r["PHCC Current"]
        delta_col = r.get("Δ Proposed–PHCC", None)
        expected_delta = p - c if pd.notna(p) and pd.notna(c) else None
        pct_col = r.get("Δ%", None)
        expected_pct = (expected_delta / c * 100) if expected_delta is not None and c != 0 else None
        d_ok = "✓" if (delta_col is None and expected_delta is None) or (abs((delta_col or 0) - (expected_delta or 0)) < 0.01) else "✗"
        p_ok = "✓" if (pct_col is None and expected_pct is None) or (abs((pct_col or 0) - (expected_pct or 0)) < 0.1) else "✗"
        print(f"    {r['HCPCS']:6s} prop={p:>8.2f} cur={c:>8.2f} "
              f"Δ={delta_col:>8.2f} exp={expected_delta:>8.2f} {d_ok} | "
              f"Δ%={pct_col:>6.1f} exp={expected_pct:>6.1f} {p_ok}")

    # 7. Flag logic validation
    print(f"  Flag logic validation:")
    errors = 0
    for _, r in matched.iterrows():
        p = r["Proposed Rate"]
        c = r["PHCC Current"]
        cms = r.get("CMS NR", np.nan)
        flag = str(r.get("Flag", ""))
        pct = (p - c) / c * 100 if c != 0 else 999

        if abs(pct) <= 1.0:
            if "NO CHANGE" not in flag:
                print(f"    ERR: {r['HCPCS']} pct={pct:.1f}% expected NO CHANGE, got: {flag}")
                errors += 1
        elif p > c:
            if "RATE INCREASE" not in flag:
                print(f"    ERR: {r['HCPCS']} p>c expected RATE INCREASE, got: {flag}")
                errors += 1
        else:
            # proposed < current
            if pd.notna(cms):
                if p >= cms:
                    if "BELOW CURRENT" not in flag:
                        print(f"    ERR: {r['HCPCS']} p<c, p>=cms expected BELOW CURRENT, got: {flag}")
                        errors += 1
                else:
                    if "BELOW CMS FLOOR" not in flag:
                        print(f"    ERR: {r['HCPCS']} p<c, p<cms expected BELOW CMS FLOOR, got: {flag}")
                        errors += 1
            else:
                if "BELOW CURRENT" not in flag:
                    print(f"    ERR: {r['HCPCS']} p<c, no cms expected BELOW CURRENT, got: {flag}")
                    errors += 1

        # PHCC BELOW CMS check
        if pd.notna(c) and pd.notna(cms) and c < cms:
            if "PHCC BELOW CMS" not in flag:
                print(f"    ERR: {r['HCPCS']} c<cms expected PHCC BELOW CMS appended, got: {flag}")
                errors += 1

    if errors == 0:
        print(f"    ✓ All {len(matched)} matched rows pass flag logic checks")
    else:
        print(f"    ✗ {errors} errors found in {len(matched)} rows")

    print()

print("VALIDATION COMPLETE")
