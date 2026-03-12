"""Quick check of clean_phcc_files.py output."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pandas as pd
from pathlib import Path

PHCC_ROOT = Path(__file__).resolve().parent.parent
OUT = PHCC_ROOT / "data" / "cleaned"

print("=== K0 ARTIFACT FOR MANUAL REVIEW ===")
k0 = pd.read_csv(OUT / "PHCC_K0_artifact_review.csv")
print(k0.to_string(index=False))

print("\n=== ALL AUDIT ISSUES BY TYPE ===")
audit = pd.read_csv(OUT / "PHCC_hcpcs_audit.csv")
print(audit["issue_type"].value_counts().to_string())

print("\n=== STILL INVALID (not fixed) ===")
invalid = audit[audit["issue_type"] == "INVALID"]
if len(invalid):
    print(invalid[["source_file","source_row","hcpcs_original","hcpcs_normalised","issue_detail"]].to_string(index=False))
else:
    print("(none)")

print("\n=== RANGE EXPANSIONS ===")
rng = pd.read_csv(OUT / "PHCC_hcpcs_range_expansion_audit.csv")
print(rng.to_string(index=False))

print("\n=== SAMPLE: CLEANED K-CODES (first 20) ===")
or_c = pd.read_csv(OUT / "PHCC_OR_CONTRACTED_CLEAN.csv")
k_rows = or_c[or_c["hcpcs_normalised"].str.startswith("K", na=False)].head(20)
print(k_rows[["hcpcs_original","hcpcs_normalised","hcpcs_is_valid","hcpcs_issue_type","modifier_normalised"]].to_string(index=False))
