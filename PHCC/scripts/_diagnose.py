import pandas as pd
from collections import Counter

df = pd.read_csv("output/fee_schedule_comparison_master.csv", dtype=str, keep_default_na=False)
print("Total rows:", len(df))
print("Review required:", df["review_required"].value_counts().to_string())
print()

reasons = df[df["review_required"]=="True"]["review_reason"]
c = Counter()
for r in reasons:
    for part in r.split("; "):
        c[part.strip()] += 1
print("Review reason breakdown:")
for reason, count in c.most_common():
    print(f"  {reason}: {count}")
print()

primary = df[df["is_primary_match"]=="True"]
print("Primary match tier distribution:")
print(primary["match_tier"].value_counts().to_string())
print()
print("Comparison status (primary only):")
print(primary["comparison_status_current"].value_counts().to_string())
