"""Quick check of raw contract file structures."""
import pandas as pd

files = [
    "data/Contract/PHCC_OR_CONTRACTED.csv",
    "data/Contract/PHCC_OR_PARTICIPATING.csv",
    "data/Contract/PHCC_WA_PARTICIPATING.csv",
]

for f in files:
    df = pd.read_csv(f, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    # Drop unnamed columns
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    print(f"--- {f} ---")
    print(f"  Rows: {len(df)}")
    print(f"  Cols: {list(df.columns)}")
    # Show mod column values
    mod_col = "Mod" if "Mod" in df.columns else "Modifier"
    mods = df[mod_col].str.strip().value_counts().to_dict()
    print(f"  Mod col: '{mod_col}', values: {mods}")
    print()
