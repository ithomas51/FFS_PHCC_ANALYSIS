"""Quick spot-check: verify Integra Note is populated for non-numeric rates."""
import pandas as pd

XLSX = r"c:\Users\ithom\Downloads\FFS_PHCC_ANALYSIS\PHCC\output\unified_code_analysis.xlsx"
df = pd.read_excel(XLSX, sheet_name="Commercial")

# Check codes with NaN Integra NU but should have a note
no_rate = df[df["Integra NU"].isna() & (df["Source"] != "PHCC_ONLY")]
has_note = no_rate["Integra Note"].notna() & (no_rate["Integra Note"] != "")
print(f"Codes with NaN Integra NU (non-PHCC_ONLY): {len(no_rate)}")
print(f"Of those, with Integra Note populated: {has_note.sum()}")
print(f"Without note: {(~has_note).sum()}")

# Sample the notes
notes = no_rate["Integra Note"].dropna()
print(f"\nTop notes:")
for n, c in notes.value_counts().head(10).items():
    print(f"  {c}: {n}")

# Also check: codes where both NU and RR are NaN
both_nan = df[(df["Integra NU"].isna()) & (df["Integra RR"].isna()) & (df["Source"] != "PHCC_ONLY")]
print(f"\nCodes with BOTH NU and RR NaN (non-PHCC_ONLY): {len(both_nan)}")
# Sample
print(both_nan[["HCPCS", "Description", "Integra Note"]].head(10))
