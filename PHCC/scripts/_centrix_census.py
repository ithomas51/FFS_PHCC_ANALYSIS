#!/usr/bin/env python3
"""Quick census of Centrix + PHCC data for validation baseline."""
import re, pandas as pd, numpy as np

cx = pd.read_csv("data/CENTRIX/Centrix_Care_OR.csv", dtype=str, keep_default_na=False)
cx.columns = [c.strip() for c in cx.columns]

print("=== CENTRIX ===")
print(f"Rows: {len(cx)}")
hcpc_valid = re.compile(r'^[A-Z][0-9]{4}$')
cx["_hcpc"] = cx["HCPC"].str.strip().str.upper()
cx["_valid"] = cx["_hcpc"].apply(lambda x: bool(hcpc_valid.match(x)))
print(f"Valid HCPC rows: {cx['_valid'].sum()}")
print(f"Invalid HCPC rows: {(~cx['_valid']).sum()}")
valid_cx = cx[cx["_valid"]]
print(f"Unique valid HCPC: {valid_cx['_hcpc'].nunique()}")
print(f"MOD1 dist: {valid_cx['MOD1'].str.strip().value_counts().to_dict()}")

# Rate patterns
rates = valid_cx["RATE"].str.strip()
def classify_rate(r):
    if not r:
        return "BLANK"
    r_clean = r.replace("$", "").replace(",", "").strip()
    try:
        float(r_clean)
        return "NUMERIC"
    except ValueError:
        if "MSRP" in r.upper():
            return "MSRP"
        return f"OTHER: {r[:40]}"

valid_cx = valid_cx.copy()
valid_cx["_rate_type"] = rates.apply(classify_rate)
print(f"\nRate types:")
for k, v in valid_cx["_rate_type"].value_counts().items():
    print(f"  {k}: {v}")

# Codes with both NU and RR
mods = valid_cx.groupby("_hcpc")["MOD1"].apply(lambda x: set(x.str.strip())).reset_index()
both_nu_rr = mods[mods["MOD1"].apply(lambda s: "NU" in s and "RR" in s)]
print(f"\nCodes with BOTH NU+RR rows: {len(both_nu_rr)}")
rr_only = mods[mods["MOD1"].apply(lambda s: "RR" in s and "NU" not in s)]
print(f"Codes with RR only (no NU): {len(rr_only)}")

print("\n=== PHCC OR CONTRACTED (cleaned) ===")
ph = pd.read_csv("data/cleaned/PHCC_OR_CONTRACTED_CLEAN.csv", dtype=str, keep_default_na=False)
valid_ph = ph[ph["hcpcs_is_valid"] == "True"]
print(f"Valid rows: {len(valid_ph)}")
print(f"Unique codes: {valid_ph['hcpcs_normalised'].nunique()}")
print(f"Mods: {valid_ph['modifier_normalised'].value_counts().to_dict()}")

# Note types
for prefix in ["Managed", "Commercial"]:
    for rate_type in ["Purchase Rate", "Rental Rate"]:
        col = f"{prefix} {rate_type}_note_type"
        if col in valid_ph.columns:
            dist = valid_ph[col].value_counts().to_dict()
            print(f"  {col}: {dist}")

# Overlap
cx_codes = set(valid_cx["_hcpc"].unique())
ph_codes = set(valid_ph["hcpcs_normalised"].unique())
print(f"\nOverlap: {len(cx_codes & ph_codes)}")
print(f"Centrix-only: {len(cx_codes - ph_codes)}")
print(f"PHCC-only: {len(ph_codes - cx_codes)}")
if len(ph_codes - cx_codes) <= 20:
    print(f"  PHCC-only codes: {sorted(ph_codes - cx_codes)}")
