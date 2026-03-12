"""Quick check on T5_RANGE NaN rows and REVIEW flag breakdown."""
import pandas as pd
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output" / "integra_rate_analysis_v2.xlsx"

df = pd.read_excel(OUT, sheet_name="Commercial", header=None)
for i in range(len(df)):
    if "HCPCS" in df.iloc[i].values:
        header_row = i
        break
df = pd.read_excel(OUT, sheet_name="Commercial", header=header_row)

# T5 with NaN PHCC rate
t5_nan = df[(df["Match"] == "T5_RANGE") & (df["PHCC Current"].isna())]
print("=== T5_RANGE with NaN PHCC Current ===")
print(f"Count: {len(t5_nan)}")
for _, r in t5_nan.head(10).iterrows():
    print(f"  {r['HCPCS']} mod={r.get('Mod','')} state={r['State']} "
          f"raw={r.get('PHCC Raw','')} flag={r['Flag']}")

# REVIEW flag breakdown
print("\n=== REVIEW flag breakdown ===")
review = df[df["Flag"].fillna("").str.contains("REVIEW", na=False)]
print(f"Count: {len(review)}")
# Group by the note content
notes = review["Note"].fillna("").value_counts()
for note, cnt in notes.head(10).items():
    print(f"  '{note[:60]}': {cnt}")

# What raw values do REVIEW rows have?
if "PHCC Raw" in review.columns:
    raws = review["PHCC Raw"].fillna("").value_counts()
    print(f"\n  PHCC Raw values in REVIEW rows:")
    for raw, cnt in raws.head(5).items():
        print(f"    '{raw[:80]}': {cnt}")

# Proposed notes in REVIEW
prop_notes = review["Note"].fillna("").value_counts()
print(f"\n  Proposed Note values in REVIEW rows:")
for n, cnt in prop_notes.head(10).items():
    print(f"    '{n[:80]}': {cnt}")
