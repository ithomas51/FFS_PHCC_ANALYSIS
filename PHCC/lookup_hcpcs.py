"""Quick HCPCS lookup for typo research."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent / "data"
CMS = BASE / "cms"
h = pd.read_csv(CMS / "2026_CMS_HCPCS.csv", dtype=str, encoding='latin1')

# E2291 range - what are the pediatric wheelchair accessory codes?
print("=== E22xx codes from E2291+ (Pediatric WC accessories) ===")
e22 = h[h['HCPC'].str.startswith('E22') & (h['HCPC'] >= 'E2291')]
print(e22[['HCPC', 'SHORT DESCRIPTION']].to_string(index=False))

print("\n=== E12xx codes (check if E1239 exists) ===")
e12 = h[h['HCPC'].str.startswith('E12')]
print(e12[['HCPC', 'SHORT DESCRIPTION']].to_string(index=False))

# L-code ranges - check endpoints
print("\n=== L-code range endpoints ===")
for code in ['L0112', 'L2861', 'L3000', 'L4631', 'L8300', 'L8485']:
    match = h[h['HCPC'] == code]
    if len(match):
        print(f"  {code}: {match.iloc[0]['SHORT DESCRIPTION']}")
    else:
        print(f"  {code}: NOT FOUND in CMS HCPCS")

# Also scan contract files for any other suspicious patterns
print("\n=== Scanning Contract files for potential typos ===")
import re
CONTRACT = BASE / "Contract"
for fname in sorted(CONTRACT.glob("*.csv")):
    df = pd.read_csv(fname, dtype=str, keep_default_na=False)
    hcpcs_col = 'HCPCS'
    for idx, row in df.iterrows():
        raw = str(row.get(hcpcs_col, '')).strip()
        if not raw:
            continue
        # Check: contains lowercase, has ?, has O where 0 expected, other oddities
        flat = re.sub(r'[\n\r]+', ' ', raw).strip()
        issues = []
        if re.search(r'[a-z]', flat):
            issues.append("lowercase")
        if '?' in flat:
            issues.append("question_mark")
        if re.search(r'^[A-Z]\d', flat) and 'O' in flat[1:]:
            issues.append("possible_O_for_0")
        # Range where end < start
        m = re.match(r'^([A-Z])(\d{4})\s*[-–—]\s*([A-Z])(\d{4})$', flat)
        if m and m.group(1) == m.group(3):
            if int(m.group(4)) < int(m.group(2)):
                issues.append(f"REVERSED_RANGE({flat})")
            elif int(m.group(4)) - int(m.group(2)) > 100:
                issues.append(f"HUGE_RANGE({int(m.group(4))-int(m.group(2))+1}_codes)")
        if issues:
            print(f"  {fname.name} row {idx+2}: '{flat}' -> {', '.join(issues)}")
