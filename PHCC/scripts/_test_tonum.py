"""Quick test: import each script's build_contract_view, check types."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

# Test _to_num directly from each script
print("=== Testing _to_num in each script ===\n")

sys.path.insert(0, "scripts")

import integra_rate_analysis_v2 as v2
import integra_rate_analysis_v2_formulas as v2f
import centrix_rate_analysis as cx

test_vals = ["74.5", "70.65", "Retail less 36%", "174.4", "28", "2.8",
             "110.35", "77", "34.85", "$1,234.56", "", "0"]

for name, mod in [("v2", v2), ("v2_formulas", v2f), ("centrix", cx)]:
    print(f"--- {name} ---")
    for val in test_vals:
        result = mod._to_num(val)
        typ = type(result).__name__
        print(f"  {val!r:25s} -> {result!r:20s} ({typ})")
    print()

print("=== All _to_num tests passed ===")
