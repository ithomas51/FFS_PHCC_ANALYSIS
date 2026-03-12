"""Validate rate patterns across Contract & Integra files."""
import pandas as pd
import itertools

DATA = r"c:\Users\ithom\Downloads\FFS_PHCC_ANALYSIS\PHCC\data"

print("=" * 70)
print("PHCC CONTRACT FILE RATE COMPARISON")
print("=" * 70)

or_c = pd.read_csv(f"{DATA}/Contract/PHCC_OR_CONTRACTED.csv", dtype=str, keep_default_na=False)
or_p = pd.read_csv(f"{DATA}/Contract/PHCC_OR_PARTICIPATING.csv", dtype=str, keep_default_na=False)
wa_p = pd.read_csv(f"{DATA}/Contract/PHCC_WA_PARTICIPATING.csv", dtype=str, keep_default_na=False)

print(f"\nOR_CONTRACTED:    {len(or_c)} rows, cols: {list(or_c.columns)}")
print(f"OR_PARTICIPATING: {len(or_p)} rows, cols: {list(or_p.columns)}")
print(f"WA_PARTICIPATING: {len(wa_p)} rows, cols: {list(wa_p.columns)}")

# OR_P vs WA_P
or_p["_key"] = or_p["HCPCS"].str.strip() + "|" + or_p.get("Modifier", pd.Series([""] * len(or_p))).astype(str).str.strip()
wa_cols = wa_p.columns.tolist()
mod_col = "Modifier" if "Modifier" in wa_cols else wa_cols[1]
wa_p["_key"] = wa_p["HCPCS"].str.strip() + "|" + wa_p[mod_col].astype(str).str.strip()

overlap = set(or_p["_key"]) & set(wa_p["_key"])
print(f"\nOR_P unique keys: {len(set(or_p['_key']))}")
print(f"WA_P unique keys: {len(set(wa_p['_key']))}")
print(f"Overlapping HCPCS+Mod keys: {len(overlap)}")

if overlap:
    or_p_idx = or_p.drop_duplicates("_key").set_index("_key")
    wa_p_idx = wa_p.drop_duplicates("_key").set_index("_key")
    same = diff = 0
    diff_examples = []
    for k in sorted(overlap):
        o_r = str(or_p_idx.at[k, "Purchase Rate"]).strip() if k in or_p_idx.index else ""
        w_r = str(wa_p_idx.at[k, "Purchase Rate"]).strip() if k in wa_p_idx.index else ""
        if o_r == w_r:
            same += 1
        else:
            diff += 1
            if diff <= 15:
                diff_examples.append((k, o_r, w_r))
    print(f"  Purchase Rate — SAME: {same}, DIFFERENT: {diff}")
    if diff_examples:
        print("  Differences:")
        for k, o, w in diff_examples:
            print(f"    {k}: OR_P={o!r}  WA_P={w!r}")

# OR_CONTRACTED vs OR_PARTICIPATING
or_c["_key"] = or_c["HCPCS"].str.strip() + "|" + or_c.get("Mod", pd.Series([""] * len(or_c))).astype(str).str.strip()
overlap2 = set(or_c["_key"]) & set(or_p["_key"])
print(f"\nOR_CONTRACTED vs OR_PARTICIPATING overlap: {len(overlap2)}")
if overlap2:
    or_c_idx = or_c.drop_duplicates("_key").set_index("_key")
    same2 = diff2 = 0
    ex2 = []
    for k in sorted(overlap2):
        if k not in or_c_idx.index or k not in or_p_idx.index:
            continue
        c_comm = str(or_c_idx.at[k, "Commercial Purchase Rate"]).strip()
        c_mgd = str(or_c_idx.at[k, "Managed Purchase Rate"]).strip()
        p_rate = str(or_p_idx.at[k, "Purchase Rate"]).strip()
        if c_comm == p_rate:
            same2 += 1
        else:
            diff2 += 1
            if diff2 <= 10:
                ex2.append((k, c_comm, c_mgd, p_rate))
    print(f"  Contracted Commercial Purchase vs Participating Purchase — SAME: {same2}, DIFF: {diff2}")
    if ex2:
        print("  Examples:")
        for k, cc, cm, pp in ex2:
            print(f"    {k}: Contracted Comm={cc!r} Mgd={cm!r}  Participating={pp!r}")

print()
print("=" * 70)
print("INTEGRA PROPOSED RATE COMPARISON")
print("=" * 70)

comm = pd.read_csv(f"{DATA}/INTEGRA_PHP_FFS/Integra_PHP_CARVEOUTS_COMMERCIAL.csv", dtype=str, keep_default_na=False)
aso = pd.read_csv(f"{DATA}/INTEGRA_PHP_FFS/Integra_PHP_CARVEOUTS_ASO.csv", dtype=str, keep_default_na=False)
mcare = pd.read_csv(f"{DATA}/INTEGRA_PHP_FFS/Integra_PHP_CARVEOUTS_MEDICARE.csv", dtype=str, keep_default_na=False)
mcaid = pd.read_csv(f"{DATA}/INTEGRA_PHP_FFS/INTEGRA_PHP_CARVEOUTS_MEDICAID.csv", dtype=str, keep_default_na=False)

for name, df in [("Commercial", comm), ("ASO", aso), ("Medicare", mcare), ("Medicaid", mcaid)]:
    print(f"{name}: {len(df)} rows, cols: {list(df.columns)}")

# Normalize keys
for df in [comm, aso, mcare, mcaid]:
    df["_key"] = df["HCPCS"].str.strip() + "|" + df["Mod 1"].str.strip()

rate_cols = {"Commercial": "Commercial", "ASO": "ASO/Commercial", "Medicare": "Medicare", "Medicaid": "Medicaid"}
dfs = [("Commercial", comm), ("ASO", aso), ("Medicare", mcare), ("Medicaid", mcaid)]

print()
for (n1, d1), (n2, d2) in itertools.combinations(dfs, 2):
    d1i = d1.drop_duplicates("_key").set_index("_key")
    d2i = d2.drop_duplicates("_key").set_index("_key")
    overlap = set(d1i.index) & set(d2i.index)
    same = diff = 0
    ex = []
    for k in sorted(overlap):
        r1 = str(d1i.at[k, rate_cols[n1]]).replace("$", "").replace(",", "").strip()
        r2 = str(d2i.at[k, rate_cols[n2]]).replace("$", "").replace(",", "").strip()
        if r1 == r2:
            same += 1
        else:
            diff += 1
            if diff <= 5:
                ex.append((k, r1, r2))
    print(f"  {n1:12s} vs {n2:12s}: overlap={len(overlap):4d}, SAME={same:4d}, DIFF={diff:4d}")
    if ex:
        for k, a, b in ex:
            print(f"      {k}: {n1}={a!r}  {n2}={b!r}")

# Check Commercial vs ASO specifically — are they truly identical?
print()
print("=" * 70)
print("COMMERCIAL vs ASO — FULL RATE IDENTITY CHECK")
print("=" * 70)
ci = comm.drop_duplicates("_key").set_index("_key")
ai = aso.drop_duplicates("_key").set_index("_key")
all_keys = sorted(set(ci.index) | set(ai.index))
only_comm = set(ci.index) - set(ai.index)
only_aso = set(ai.index) - set(ci.index)
both = set(ci.index) & set(ai.index)
print(f"Only in Commercial: {len(only_comm)}")
print(f"Only in ASO: {len(only_aso)}")
print(f"In both: {len(both)}")
identical = sum(1 for k in both if str(ci.at[k, 'Commercial']).replace('$','').strip() == str(ai.at[k, 'ASO/Commercial']).replace('$','').strip())
print(f"Identical rates: {identical} / {len(both)}")
