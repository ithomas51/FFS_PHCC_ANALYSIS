"""Quick check: how many Integra rates are numeric vs text per payer."""
import pandas as pd

files = {
    "Commercial": ("data/INTEGRA_PHP_FFS/Integra_PHP_CARVEOUTS_COMMERCIAL.csv", "Commercial"),
    "ASO": ("data/INTEGRA_PHP_FFS/Integra_PHP_CARVEOUTS_ASO.csv", "ASO/Commercial"),
    "Medicare": ("data/INTEGRA_PHP_FFS/Integra_PHP_CARVEOUTS_MEDICARE.csv", "Medicare"),
    "Medicaid": ("data/INTEGRA_PHP_FFS/INTEGRA_PHP_CARVEOUTS_MEDICAID.csv", "Medicaid"),
}

for payer, (path, col) in files.items():
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df.columns = [c.strip() for c in df.columns]

    # Split into non-RR (NU) and RR
    mod = df["Mod 1"].str.strip().str.upper().fillna("")
    nu_rows = df[mod != "RR"]
    rr_rows = df[mod == "RR"]

    nu_numeric = 0
    nu_text = {}
    for v in nu_rows[col].str.strip():
        s = v.replace("$", "").replace(",", "")
        try:
            float(s)
            nu_numeric += 1
        except ValueError:
            nu_text[v] = nu_text.get(v, 0) + 1

    # Deduplicate by HCPCS for unique code count
    nu_codes = nu_rows["HCPCS"].str.strip().str.upper().nunique()

    print(f"=== {payer} ({col}) ===")
    print(f"  NU rows: {len(nu_rows)}, RR rows: {len(rr_rows)}")
    print(f"  NU unique codes: {nu_codes}")
    print(f"  NU numeric rates: {nu_numeric}")
    print(f"  NU non-numeric rates: {len(nu_rows) - nu_numeric}")
    print(f"  Top non-numeric:")
    for k, c in sorted(nu_text.items(), key=lambda x: -x[1])[:5]:
        print(f"    {c}: {repr(k)}")
    print()
