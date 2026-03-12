"""
Test & validation suite for analyze_fee_schedules.py (v2)
==========================================================
Tests pure functions, data quality, and spot-checks known values.

Run:  python test_fee_schedules.py
"""

import sys
import numpy as np
from pathlib import Path

# Import from PHCC/scripts/ where analyze_fee_schedules.py lives
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "PHCC" / "scripts"))

from analyze_fee_schedules import (
    normalize_hcpcs,
    validate_hcpcs,
    parse_hcpcs_range,
    safe_float,
    classify_pricing_note,
    norm_mod,
    compare_rates,
    compare_to_benchmark,
    FILES,
)

passed = 0
failed = 0


def check(label, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {label}")
        print(f"    Expected: {expected!r}")
        print(f"    Actual:   {actual!r}")


def check_approx(label, actual, expected, tol=0.01):
    global passed, failed
    if (np.isnan(actual) and np.isnan(expected)):
        passed += 1
    elif abs(actual - expected) < tol:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {label}")
        print(f"    Expected: {expected!r}")
        print(f"    Actual:   {actual!r}")


# ════════════════════════════════════════════════════════════════════════
print("\n[1] normalize_hcpcs")
# ════════════════════════════════════════════════════════════════════════
check("basic upper", normalize_hcpcs("e0100"), "E0100")
check("strip spaces", normalize_hcpcs("  A4253  "), "A4253")
check("KO→K0 OCR fix", normalize_hcpcs("KO001"), "K0001")
check("empty string", normalize_hcpcs(""), "")
check("None", normalize_hcpcs(None), "")
check("line breaks", normalize_hcpcs("E0\n100"), "E0100")

# ════════════════════════════════════════════════════════════════════════
print("\n[2] validate_hcpcs")
# ════════════════════════════════════════════════════════════════════════
check("valid code", validate_hcpcs("E0100"), (True, ""))
check("valid A code", validate_hcpcs("A4253"), (True, ""))
check("valid K code", validate_hcpcs("K0001"), (True, ""))
check("empty", validate_hcpcs(""), (False, "EMPTY"))
check("range", validate_hcpcs("E2601-E2610"), (False, "RANGE"))
check("OCR ?", validate_hcpcs("KOO??"), (False, "OCR_ARTIFACT"))
check("bad length 4", validate_hcpcs("E010"), (False, "BAD_LENGTH_4"))
check("bad length 6", validate_hcpcs("E01001"), (False, "BAD_LENGTH_6"))

# ════════════════════════════════════════════════════════════════════════
print("\n[3] parse_hcpcs_range")
# ════════════════════════════════════════════════════════════════════════
codes, rs, re_ = parse_hcpcs_range("E2601-E2610")
check("range count", len(codes) if codes else 0, 10)
check("range first", codes[0] if codes else None, "E2601")
check("range last", codes[-1] if codes else None, "E2610")
check("range start", rs, "E2601")
check("range end", re_, "E2610")

codes2, _, _ = parse_hcpcs_range("K0001 - K0007")
check("range with spaces", len(codes2) if codes2 else 0, 7)

codes3, _, _ = parse_hcpcs_range("A4253")
check("not a range", codes3, None)

codes4, _, _ = parse_hcpcs_range("E0100-L0200")
check("different prefixes", codes4, None)

# ════════════════════════════════════════════════════════════════════════
print("\n[4] safe_float")
# ════════════════════════════════════════════════════════════════════════
check_approx("dollar sign", safe_float("$123.45"), 123.45)
check_approx("no dollar", safe_float("123.45"), 123.45)
check_approx("comma", safe_float("$1,234.56"), 1234.56)
check_approx("nan for text", safe_float("Retail less 30%"), np.nan)
check_approx("nan for empty", safe_float(""), np.nan)
check_approx("nan for None", safe_float(None), np.nan)
check_approx("zero", safe_float("$0.00"), 0.0)

# ════════════════════════════════════════════════════════════════════════
print("\n[5] classify_pricing_note")
# ════════════════════════════════════════════════════════════════════════
check("numeric returns empty", classify_pricing_note("$123.45"), ("", ""))
check("retail less 30%", classify_pricing_note("Retail less 30%")[0], "PERCENT_OF_RETAIL")
check("non-billable", classify_pricing_note("Non-billable")[0], "NON_BILLABLE")
check("quote", classify_pricing_note("Quote")[0], "QUOTE_REQUIRED")
check("per 15 min", classify_pricing_note("$15.40 per 15 min")[0], "PER_TIME_UNIT")
check("medicare allowable", classify_pricing_note("Medicare Allowable less 20%")[0], "PERCENT_OF_MEDICARE_ALLOWABLE")
check("prevailing", classify_pricing_note("Prevailing State Rates")[0], "PREVAILING_STATE_RATES")
check("prevailng typo", classify_pricing_note("Prevailng State Rates")[0], "PREVAILING_STATE_RATES")
check("empty", classify_pricing_note(""), ("", ""))

# ════════════════════════════════════════════════════════════════════════
print("\n[6] compare_rates")
# ════════════════════════════════════════════════════════════════════════
check("higher", compare_rates(150.0, 100.0), ("HIGHER", 50.0, 50.0))
check("lower", compare_rates(80.0, 100.0), ("LOWER", -20.0, -20.0))
check("equal", compare_rates(100.0, 100.0), ("EQUAL", 0.0, 0.0))
s, d, p = compare_rates(np.nan, 100.0)
check("nan proposed", s, "NOT_COMPARABLE")
s2, _, _ = compare_rates(100.0, 0.0)
check("zero current", s2, "NOT_COMPARABLE")

# ════════════════════════════════════════════════════════════════════════
print("\n[7] compare_to_benchmark")
# ════════════════════════════════════════════════════════════════════════
check("above bench", compare_to_benchmark(120.0, 100.0, "CMS")[0], "ABOVE_BENCHMARK")
check("below bench", compare_to_benchmark(80.0, 100.0, "CMS")[0], "BELOW_BENCHMARK")
check("equal bench", compare_to_benchmark(100.0, 100.0, "CMS")[0], "EQUAL_TO_BENCHMARK")
s3, _, _ = compare_to_benchmark(80.0, np.nan, "CMS")
check("missing bench", s3, "MISSING_BENCHMARK")

# ════════════════════════════════════════════════════════════════════════
print("\n[8] Data file existence checks")
# ════════════════════════════════════════════════════════════════════════
for name, path in FILES.items():
    check(f"exists: {name}", path.exists(), True)

# ════════════════════════════════════════════════════════════════════════
print("\n[9] Data integrity: Integra row counts should be equal across payers")
# ════════════════════════════════════════════════════════════════════════
import pandas as pd

counts = {}
for key in ["integra_commercial", "integra_medicare", "integra_medicaid", "integra_aso"]:
    df = pd.read_csv(FILES[key], dtype=str, keep_default_na=False)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    counts[key] = len(df)

base_count = counts["integra_commercial"]
for k, v in counts.items():
    check(f"row count {k}={base_count}", v, base_count)

# ════════════════════════════════════════════════════════════════════════
print("\n[10] HCPCS code overlap: Integra vs PHCC")
# ════════════════════════════════════════════════════════════════════════
integra_codes = set()
for key in ["integra_commercial"]:
    df = pd.read_csv(FILES[key], dtype=str, keep_default_na=False)
    for _, r in df.iterrows():
        code = normalize_hcpcs(r.get("HCPCS", ""))
        v, _ = validate_hcpcs(code)
        if v:
            integra_codes.add(code)

phcc_or_codes = set()
df_or = pd.read_csv(FILES["phcc_or"], dtype=str, keep_default_na=False)
for _, r in df_or.iterrows():
    code = normalize_hcpcs(r.get("HCPCS", ""))
    v, iss = validate_hcpcs(code)
    if v:
        phcc_or_codes.add(code)
    elif iss == "RANGE":
        codes, _, _ = parse_hcpcs_range(r.get("HCPCS", ""))
        if codes:
            phcc_or_codes.update(codes)

phcc_wa_codes = set()
df_wa = pd.read_csv(FILES["phcc_wa"], dtype=str, keep_default_na=False)
for _, r in df_wa.iterrows():
    code = normalize_hcpcs(r.get("HCPCS", ""))
    v, iss = validate_hcpcs(code)
    if v:
        phcc_wa_codes.add(code)
    elif iss == "RANGE":
        codes, _, _ = parse_hcpcs_range(r.get("HCPCS", ""))
        if codes:
            phcc_wa_codes.update(codes)

overlap_or = integra_codes & phcc_or_codes
overlap_wa = integra_codes & phcc_wa_codes

print(f"  Integra valid codes: {len(integra_codes)}")
print(f"  PHCC_OR codes (incl. expanded): {len(phcc_or_codes)}")
print(f"  PHCC_WA codes (incl. expanded): {len(phcc_wa_codes)}")
print(f"  OR overlap: {len(overlap_or)}")
print(f"  WA overlap: {len(overlap_wa)}")

# Sanity: we expect significant overlap (at least E/K codes)
check("OR overlap > 50", len(overlap_or) > 50, True)
check("WA overlap > 50", len(overlap_wa) > 50, True)

# ════════════════════════════════════════════════════════════════════════
print("\n[11] Spot-check: known code E0100 in Integra Commercial")
# ════════════════════════════════════════════════════════════════════════
df_comm = pd.read_csv(FILES["integra_commercial"], dtype=str, keep_default_na=False)
df_comm.columns = [c.strip() for c in df_comm.columns]
e0100 = df_comm[df_comm["HCPCS"].str.strip().str.upper() == "E0100"]
if len(e0100) > 0:
    rate = safe_float(e0100.iloc[0]["Commercial"])
    check("E0100 has a numeric commercial rate", not np.isnan(rate), True)
    print(f"  E0100 Commercial rate: ${rate:.2f}")
else:
    print("  WARNING: E0100 not found in Integra Commercial")

# ════════════════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"TESTS COMPLETE:  {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    print("\nSome tests FAILED — review output above.")
    sys.exit(1)
else:
    print("\nAll tests PASSED.")
    sys.exit(0)
