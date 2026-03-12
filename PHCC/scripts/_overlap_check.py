"""Quick HCPCS overlap check: OR_CONTRACTED vs OR_PARTICIPATING."""
import pandas as pd

or_c = pd.read_csv("data/Contract/PHCC_OR_CONTRACTED.csv", dtype=str, keep_default_na=False)
or_p = pd.read_csv("data/Contract/PHCC_OR_PARTICIPATING.csv", dtype=str, keep_default_na=False)
wa_p = pd.read_csv("data/Contract/PHCC_WA_PARTICIPATING.csv", dtype=str, keep_default_na=False)

# Pure HCPCS overlap (ignoring modifier)
c_codes = set(or_c["HCPCS"].str.strip())
p_codes = set(or_p["HCPCS"].str.strip())
w_codes = set(wa_p["HCPCS"].str.strip())

print(f"OR_C unique HCPCS: {len(c_codes)}")
print(f"OR_P unique HCPCS: {len(p_codes)}")
print(f"WA_P unique HCPCS: {len(w_codes)}")
print(f"OR_C ∩ OR_P: {len(c_codes & p_codes)}")
print(f"OR_C ∩ WA_P: {len(c_codes & w_codes)}")
print(f"OR_P ∩ WA_P: {len(p_codes & w_codes)}")
print(f"All three: {len(c_codes & p_codes & w_codes)}")

# For overlapping codes between OR_P and WA_P, compare rates
overlap_pw = c_codes & p_codes
if overlap_pw:
    print(f"\nOR_C vs OR_P HCPCS overlap (code-only): {len(overlap_pw)}")
    # Grab some samples
    or_c_sample = or_c[or_c["HCPCS"].str.strip().isin(list(overlap_pw)[:5])]
    or_p_sample = or_p[or_p["HCPCS"].str.strip().isin(list(overlap_pw)[:5])]
    print("\n  OR_C samples:")
    for _, r in or_c_sample.head(5).iterrows():
        print(f"    {r['HCPCS'].strip()} | Mod={r['Mod'].strip()!r} | CommPurch={r['Commercial Purchase Rate'].strip()!r} | MgdPurch={r['Managed Purchase Rate'].strip()!r}")
    print("  OR_P samples:")
    for _, r in or_p_sample.head(5).iterrows():
        print(f"    {r['HCPCS'].strip()} | Mod={r['Modifier'].strip()!r} | Purchase={r['Purchase Rate'].strip()!r}")

# HCPCS ranges in raw data
print("\nHCPCS range entries (containing '-'):")
for name, df, col in [("OR_C", or_c, "HCPCS"), ("OR_P", or_p, "HCPCS"), ("WA_P", wa_p, "HCPCS")]:
    ranges = df[df[col].str.contains("-", na=False)]
    print(f"  {name}: {len(ranges)} range entries")
    for _, r in ranges.head(3).iterrows():
        print(f"    {r[col].strip()}")

# Unique modifier values
print("\nModifier values:")
for name, df, col in [("OR_C", or_c, "Mod"), ("OR_P", or_p, "Modifier"), ("WA_P", wa_p, "Modifier")]:
    mods = df[col].str.strip().unique()
    print(f"  {name}: {sorted(mods)}")
