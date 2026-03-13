"""Exact code/modifier census for planning the unified script."""
import pandas as pd
from pathlib import Path
ROOT = Path(r"c:\Users\ithom\Downloads\FFS_PHCC_ANALYSIS\PHCC")

# ── Integra ──
integra_codes = set()
for f, col in [("Integra_PHP_CARVEOUTS_COMMERCIAL.csv", "Commercial"),
               ("Integra_PHP_CARVEOUTS_ASO.csv", "ASO/Commercial"),
               ("Integra_PHP_CARVEOUTS_MEDICARE.csv", "Medicare"),
               ("INTEGRA_PHP_CARVEOUTS_MEDICAID.csv", "Medicaid")]:
    df = pd.read_csv(ROOT/"data"/"INTEGRA_PHP_FFS"/f, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    codes = df["HCPCS"].str.strip().str.upper().dropna()
    codes = codes[codes != ""]
    integra_codes.update(codes)
    mods = df["Mod 1"].str.strip().str.upper().fillna("")
    print(f"Integra {col}: {len(codes)} rows, {codes.nunique()} unique codes")
    print(f"  Modifiers: {dict(mods.value_counts().head(10))}")

print(f"\nIntegra TOTAL unique codes: {len(integra_codes)}")

# ── PHCC Cleaned ──
phcc_codes = set()
for f in ["PHCC_OR_CONTRACTED_CLEAN.csv", "PHCC_OR_PARTICIPATING_CLEAN.csv",
          "PHCC_WA_PARTICIPATING_CLEAN.csv"]:
    df = pd.read_csv(ROOT/"data"/"cleaned"/f, dtype=str, keep_default_na=False)
    valid = df[df["hcpcs_is_valid"] == "True"]
    codes = valid["hcpcs_normalised"].str.strip().str.upper()
    phcc_codes.update(codes)
    mods = valid["modifier_normalised"].str.strip().str.upper().fillna("")
    issue = df["hcpcs_issue_type"].str.strip()
    category = df[issue == "CATEGORY_RANGE"]
    print(f"\n{f}: {len(df)} rows, {codes.nunique()} valid codes, "
          f"{len(category)} CATEGORY_RANGE rows")
    print(f"  Modifiers: {dict(mods.value_counts())}")
    # Rate note types
    for ratecol in ["Purchase Rate_note_type", "Rental Rate_note_type",
                    "Managed Purchase Rate_note_type", "Commercial Purchase Rate_note_type"]:
        if ratecol in df.columns:
            types = df[ratecol].str.strip()
            types = types[types != ""]
            if len(types) > 0:
                print(f"  {ratecol}: {dict(types.value_counts())}")

print(f"\nPHCC TOTAL unique valid codes: {len(phcc_codes)}")

# ── CMS ──
for f, nr, r in [("CMS_2026_Q1_OR.csv", "OR (NR)", "OR (R)"),
                  ("CMS_2026_Q1_WA.csv", "WA (NR)", "WA (R)")]:
    df = pd.read_csv(ROOT/"data"/"cms"/f, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    codes = df["HCPCS"].str.strip().str.upper()
    mods = df["Mod"].str.strip().str.upper().fillna("")
    print(f"\n{f}: {len(df)} rows, {codes.nunique()} unique codes")
    print(f"  Modifiers: {dict(mods.value_counts().head(10))}")

# ── OHA ──
df = pd.read_csv(ROOT/"data"/"cms"/"OHA_FFS_09_2025_RAW.csv", dtype=str, keep_default_na=False)
df.columns = [c.strip() for c in df.columns]
codes = df["Procedure Code"].str.strip().str.upper()
mods = df["Mod1"].str.strip().str.upper().fillna("")
print(f"\nOHA: {len(df)} rows, {codes.nunique()} unique codes")
print(f"  Modifiers: {dict(mods.value_counts().head(10))}")

# ── Overlap analysis ──
union = integra_codes | phcc_codes
overlap = integra_codes & phcc_codes
integra_only = integra_codes - phcc_codes
phcc_only = phcc_codes - integra_codes

print(f"\n{'='*50}")
print(f"UNION (all unique codes):     {len(union)}")
print(f"OVERLAP (in both):            {len(overlap)}")
print(f"INTEGRA only:                 {len(integra_only)}")
print(f"PHCC only:                    {len(phcc_only)}")
print(f"{'='*50}")
print(f"\nOverlapping codes sample: {sorted(list(overlap))[:20]}")
print(f"Integra-only sample: {sorted(list(integra_only))[:20]}")
print(f"PHCC-only sample: {sorted(list(phcc_only))[:20]}")
