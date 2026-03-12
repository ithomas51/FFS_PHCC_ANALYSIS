"""
PHCC Fee Schedule CSV Cleaner
=============================
Reads all three PHCC source CSVs, normalises HCPCS codes, expands code
ranges, flattens compound modifiers (NU/RR → two rows), fixes OCR
artifacts, and writes cleaned CSVs plus a manual-review artifact.

Outputs (written to PHCC/data/cleaned/):
  PHCC_OR_CONTRACTED_CLEAN.csv
  PHCC_OR_PARTICIPATING_CLEAN.csv
  PHCC_WA_PARTICIPATING_CLEAN.csv
  PHCC_hcpcs_range_expansion_audit.csv
  PHCC_hcpcs_audit.csv
  PHCC_K0_artifact_review.csv      ← K-code OCR corrections for manual sign-off

Run:  python clean_phcc_files.py
Requires: pip install pandas
"""

import pandas as pd
import numpy as np
import re
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent / "data" / "Contract"
OUT  = Path(__file__).resolve().parent / "data" / "cleaned"
OUT.mkdir(exist_ok=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1.  OCR CORRECTION TABLE  (letter-O → digit-0, ? → best guess)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Built by reading every K-code row in PHCC_OR_CONTRACTED.csv and matching
# the description to the official CMS HCPCS Short Description list.
# Rules:
#   • "O"  after first char treated as digit "0" when position expects digit
#   • "?"  resolved by description context against HCPCS reference
#   • All corrections verified against CMS 2026_CMS_HCPCS.csv
OCR_CORRECTIONS = {
    # code_as_scanned  →  (corrected, confidence, note)
    "KOOO?":  ("K0007", "HIGH", "Description matches K0007 'Manual WC extra-heavy duty'"),
    "KOO17":  ("K0017", "HIGH", "O→0: Detachable, non-adjustable height armrest base"),
    "KOO18":  ("K0018", "HIGH", "O→0: Detachable, adjustable height armrest upper"),
    "KOO19":  ("K0019", "HIGH", "O→0: Arm pad"),
    "KOO2O":  ("K0020", "HIGH", "O→0: Fixed adjustable height armrest pair"),
    "KOO37":  ("K0037", "HIGH", "O→0: High mount flip-up footrest"),
    "KOO38":  ("K0038", "HIGH", "O→0: Leg strap each"),
    "KOO39":  ("K0039", "HIGH", "O→0: Leg strap h style each"),
    "KOO4O":  ("K0040", "HIGH", "O→0: Adjustable angle footplate"),
    "KOO41":  ("K0041", "HIGH", "O→0: Large size footplate each"),
    "KOO42":  ("K0042", "HIGH", "O→0: Standard size footplate each"),
    "KOO43":  ("K0043", "HIGH", "O→0: Footrest lower extension tube"),
    "KOO44":  ("K0044", "HIGH", "O→0: Footrest upper hanger bracket"),
    "KOO45":  ("K0045", "HIGH", "O→0: Footrest complete assembly"),
    "KOO46":  ("K0046", "HIGH", "O→0: Elevating legrest lower extension"),
    "KOO47":  ("K0047", "HIGH", "O→0: Elevating legrest upper hanger bracket"),
    "KOO5O":  ("K0050", "HIGH", "O→0: Ratchet assembly"),
    "KOO51":  ("K0051", "HIGH", "O→0: Cam release assembly"),
    "KOO52":  ("K0052", "HIGH", "O→0: Swingaway detachable footrest"),
    "KOO53":  ("K0053", "HIGH", "O→0: Elevating footrest articulating"),
    "KOO56":  ("K0056", "HIGH", "O→0: Seat height under 17in / 21in+"),
    "KOO65":  ("K0065", "HIGH", "O→0: Spoke protectors"),
    "KOO69":  ("K0069", "HIGH", "O→0: Rear wheel assembly complete, solid tire"),
    "KOO7O":  ("K0070", "HIGH", "O→0: Rear wheel assembly complete, pneumatic"),
    "KOO71":  ("K0071", "HIGH", "O→0: Front caster assembly, pneumatic tire"),
    "KOO72":  ("K0072", "HIGH", "O→0: Front caster assembly, semi-pneumatic"),
    "KOO73":  ("K0073", "HIGH", "O→0: Caster pin lock"),
    "KOO??":  ("K0074", "MEDIUM", "Guessed from description 'Front caster assembly, solid tire'"),
    "KOO98":  ("K0098", "HIGH", "O→0: Drive belt power for wheelchair"),
    "KO1O5":  ("K0105", "HIGH", "O→0: IV hanger"),
    "KO1O8":  ("K0108", "HIGH", "O→0: WC component/accessory NOS"),
    "KO195":  ("K0195", "HIGH", "O→0: Elevating legrests"),
    "KO462":  ("K0462", "HIGH", "O→0: Temporary replacement for patient owned equip"),
    "KO739":  ("K0739", "HIGH", "O→0: Labor repair DME"),
    "KO8OO":  ("K0800", "HIGH", "O→0: POV group 1 standard"),
    "KO8O1":  ("K0801", "HIGH", "O→0: POV group 1 heavy duty"),
    "KOO?O":  ("K0070", "HIGH", "?→7, O→0: Rear wheel assembly, pneumatic tire (WA)"),
    "KOSO?":  ("K0807", "MEDIUM", "S→8, O→0, ?→7: POV group 2 heavy duty 301-450 lbs"),
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2.  HCPCS CODE CLEANING HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALID_HCPCS = re.compile(r'^[A-Z][0-9]{4}$')

# Pattern for ranges like "E2624 - E2625", "A6544-A6549", "A7520-A7522"
RANGE_PATTERN = re.compile(
    r'^([A-Z]\d{4})\s*[-–—]\s*([A-Z]\d{4})$'
)

# Pattern for trailing-dash codes like "E1035-", "E2216-", "E2291-", "E2601--"
TRAILING_DASH = re.compile(r'^([A-Z]\d{4})\s*[-–—]+\s*$')

# Pattern for messy codes like "E- 1017--" or "E-1035 - ---"
EMBEDDED_JUNK = re.compile(r'^([A-Z])[\s\-–—]+(\d{4})[\s\-–—]*$')

# Pattern for multiline / OCR artifacts like "A7000\nSuction"
MULTILINE_HCPCS = re.compile(r'^([A-Z]\d{4})\s*[\n\r]', re.MULTILINE)


def normalise_hcpcs(raw: str) -> tuple:
    """
    Returns (normalised_code_or_list, issue_type, issue_detail, expanded_from_range, range_start, range_end).
    If a range, returns a list of codes. Otherwise a single string.
    """
    if pd.isna(raw) or str(raw).strip() == "":
        return "", "EMPTY", "No HCPCS code", False, "", ""

    s = str(raw).strip().upper()
    # Remove embedded newlines for matching
    s_flat = re.sub(r'[\n\r]+', ' ', s).strip()

    # ── Check OCR correction table first ──
    if s_flat in OCR_CORRECTIONS:
        corrected, confidence, note = OCR_CORRECTIONS[s_flat]
        return corrected, "OCR_CORRECTED", f"{note} [confidence={confidence}]", False, "", ""

    # ── Try direct valid match ──
    if VALID_HCPCS.match(s_flat):
        return s_flat, "", "", False, "", ""

    # ── Multiline: extract first valid code ──
    m = MULTILINE_HCPCS.match(s)
    if m:
        code = m.group(1).upper()
        return code, "MULTILINE_CLEANED", f"Extracted from multiline: {repr(raw)}", False, "", ""

    # ── Range: "E2624 - E2625" ──
    m = RANGE_PATTERN.match(s_flat)
    if m:
        start, end = m.group(1), m.group(2)
        codes = expand_range(start, end)
        if codes == "CATEGORY":
            return s_flat, "CATEGORY_RANGE", f"Large catch-all range kept as-is: {start}-{end}", False, start, end
        elif codes is not None:
            return codes, "RANGE_EXPANDED", f"{start}-{end}", True, start, end
        else:
            return s_flat, "MALFORMED_RANGE", f"Could not expand: {start}-{end}", False, start, end

    # ── Trailing dash: "E1035-" → E1035 ──
    m = TRAILING_DASH.match(s_flat)
    if m:
        code = m.group(1)
        return code, "TRAILING_DASH_REMOVED", f"Original: {repr(raw)}", False, "", ""

    # ── Embedded junk: "E- 1017--" → E1017 ──
    m = EMBEDDED_JUNK.match(s_flat)
    if m:
        code = m.group(1) + m.group(2)
        if VALID_HCPCS.match(code):
            return code, "JUNK_CHARS_REMOVED", f"Cleaned from: {repr(raw)}", False, "", ""

    # ── Generic O→0 fallback for any remaining K-codes ──
    if s_flat.startswith("K"):
        candidate = s_flat[0] + re.sub(r'O', '0', s_flat[1:])
        candidate = re.sub(r'[^A-Z0-9]', '', candidate)
        if VALID_HCPCS.match(candidate):
            return candidate, "OCR_GENERIC_O_TO_0", f"Auto-corrected O→0: {repr(raw)}", False, "", ""

    # ── Could not fix ──
    return s_flat, "INVALID", f"Could not normalise: {repr(raw)}", False, "", ""


def expand_range(start: str, end: str):
    """Expand A6530-A6541 → [A6530, A6531, ..., A6541]. Returns None if invalid, 'CATEGORY' if >100 codes."""
    if start[0] != end[0]:
        return None  # Different alpha prefix
    prefix = start[0]
    try:
        n1 = int(start[1:])
        n2 = int(end[1:])
    except ValueError:
        return None
    if n2 < n1:
        return None  # Reversed range = typo
    if (n2 - n1) > 100:
        return "CATEGORY"  # Intentional catch-all category range
    return [f"{prefix}{str(i).zfill(4)}" for i in range(n1, n2 + 1)]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3.  MODIFIER FLATTENING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def flatten_modifier(mod_raw: str) -> list:
    """
    "NU/RR"  → ["NU", "RR"]
    "NU**"   → ["NU"]
    "NU"     → ["NU"]
    ""       → [""]
    """
    if pd.isna(mod_raw) or str(mod_raw).strip() == "":
        return [""]
    s = str(mod_raw).strip().upper()
    # Remove trailing asterisks (NU** → NU)
    s = re.sub(r'\*+$', '', s).strip()
    # Split on /
    parts = [p.strip() for p in s.split("/") if p.strip()]
    return parts if parts else [""]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4.  PRICING NOTE CLASSIFIER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def classify_rate(val):
    """Returns (numeric_value_or_NaN, note_type, note_detail)."""
    if pd.isna(val):
        return np.nan, "", ""
    s = str(val).strip()
    if s == "" or s.lower() == "nan":
        return np.nan, "", ""

    # Try numeric parse
    cleaned = s.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned), "NUMERIC", ""
    except ValueError:
        pass

    su = s.upper().strip()
    if "NON-BILLABLE" in su or "NON BILLABLE" in su:
        return np.nan, "NON_BILLABLE", s
    if re.match(r'RETAIL\s+LESS\s+(\d+)%', su):
        m = re.match(r'RETAIL\s+LESS\s+(\d+)%', su)
        return np.nan, "PERCENT_OF_RETAIL", f"Retail less {m.group(1)}%"
    if "QUOTE" in su:
        return np.nan, "QUOTE_REQUIRED", s
    if "MEDICARE ALLOWABLE" in su:
        return np.nan, "PERCENT_OF_MEDICARE_ALLOWABLE", s
    if "PREVAIL" in su:
        return np.nan, "PREVAILING_STATE_RATES", s
    if "COST INVOICE" in su:
        return np.nan, "COST_INVOICE", s
    if "PER 15 MIN" in su or "PER MIN" in su:
        return np.nan, "PER_TIME_UNIT", s

    return np.nan, "UNPARSED_TEXT", s


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5.  FILE PROCESSORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

audit_rows = []        # hcpcs issues
range_audit_rows = []  # expanded ranges

def process_file(path: Path, source_label: str, hcpcs_col: str, mod_col: str, rate_cols: list):
    """
    Generic processor. Reads CSV, normalises HCPCS, flattens modifiers,
    expands ranges, classifies rates, returns cleaned DataFrame.
    """
    global audit_rows, range_audit_rows

    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    # Drop unnamed filler columns
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df.columns = [c.strip() for c in df.columns]

    out_rows = []

    for row_idx, row in df.iterrows():
        raw_hcpcs = row.get(hcpcs_col, "")
        raw_mod = row.get(mod_col, "")

        # Normalise HCPCS
        hcpcs_result, issue_type, issue_detail, is_range, rng_start, rng_end = normalise_hcpcs(raw_hcpcs)

        # Track issues
        if issue_type and issue_type not in ("", "RANGE_EXPANDED"):
            audit_rows.append({
                "source_file": source_label,
                "source_row": row_idx + 2,  # +2 for 1-based + header
                "hcpcs_original": raw_hcpcs,
                "hcpcs_normalised": hcpcs_result if isinstance(hcpcs_result, str) else str(hcpcs_result),
                "issue_type": issue_type,
                "issue_detail": issue_detail,
            })

        # Build list of codes (range → list)
        if isinstance(hcpcs_result, list):
            codes = hcpcs_result
            for c in codes:
                range_audit_rows.append({
                    "source_file": source_label,
                    "source_row": row_idx + 2,
                    "hcpcs_original": raw_hcpcs,
                    "expanded_code": c,
                    "range_start": rng_start,
                    "range_end": rng_end,
                })
        else:
            codes = [hcpcs_result]

        # Flatten modifiers
        mods = flatten_modifier(raw_mod)

        # Classify rates
        rate_classified = {}
        for rc in rate_cols:
            val = row.get(rc, "")
            num, note_type, note_detail = classify_rate(val)
            rate_classified[rc] = (val, num, note_type, note_detail)

        # Explode: one row per (code, modifier) combination
        for code in codes:
            for mod in mods:
                new_row = {
                    "source_file": source_label,
                    "source_row": row_idx + 2,
                    "hcpcs_original": raw_hcpcs,
                    "hcpcs_normalised": code,
                    "hcpcs_is_valid": bool(VALID_HCPCS.match(code)) if code else False,
                    "hcpcs_issue_type": issue_type,
                    "expanded_from_range": is_range,
                    "range_start": rng_start,
                    "range_end": rng_end,
                    "modifier_original": raw_mod,
                    "modifier_normalised": mod,
                }

                # Copy all original columns except HCPCS and Mod
                for col in df.columns:
                    if col not in (hcpcs_col, mod_col):
                        new_row[f"orig_{col}"] = row.get(col, "")

                # Add classified rate columns
                for rc in rate_cols:
                    raw_val, num_val, ntype, ndetail = rate_classified[rc]
                    new_row[f"{rc}_raw"] = raw_val
                    new_row[f"{rc}_numeric"] = num_val
                    new_row[f"{rc}_note_type"] = ntype
                    new_row[f"{rc}_note_detail"] = ndetail

                out_rows.append(new_row)

    return pd.DataFrame(out_rows)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6.  MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print("=" * 60)
    print("PHCC Fee Schedule CSV Cleaner")
    print("=" * 60)

    # ── PHCC_OR_CONTRACTED ──
    print("\n[1/3] Cleaning PHCC_OR_CONTRACTED.csv …")
    or_contr = process_file(
        BASE / "PHCC_OR_CONTRACTED.csv",
        source_label="PHCC_OR_CONTRACTED",
        hcpcs_col="HCPCS",
        mod_col="Mod",
        rate_cols=["Managed Rental Rate", "Managed Purchase Rate",
                   "Commercial Rental Rate", "Commercial Purchase Rate"],
    )
    or_contr.to_csv(OUT / "PHCC_OR_CONTRACTED_CLEAN.csv", index=False)
    print(f"   → {len(or_contr)} rows written")

    # ── PHCC_OR_PARTICIPATING ──
    print("\n[2/3] Cleaning PHCC_OR_PARTICIPATING.csv …")
    or_part = process_file(
        BASE / "PHCC_OR_PARTICIPATING.csv",
        source_label="PHCC_OR_PARTICIPATING",
        hcpcs_col="HCPCS",
        mod_col="Modifier",
        rate_cols=["Rental Rate", "Purchase Rate"],
    )
    or_part.to_csv(OUT / "PHCC_OR_PARTICIPATING_CLEAN.csv", index=False)
    print(f"   → {len(or_part)} rows written")

    # ── PHCC_WA_PARTICIPATING ──
    print("\n[3/3] Cleaning PHCC_WA_PARTICIPATING.csv …")
    wa_part = process_file(
        BASE / "PHCC_WA_PARTICIPATING.csv",
        source_label="PHCC_WA_PARTICIPATING",
        hcpcs_col="HCPCS",
        mod_col="Modifier",
        rate_cols=["Rental Rate", "Purchase Rate"],
    )
    wa_part.to_csv(OUT / "PHCC_WA_PARTICIPATING_CLEAN.csv", index=False)
    print(f"   → {len(wa_part)} rows written")

    # ── Audit files ──
    print("\n[Audit] Writing audit files …")
    audit_df = pd.DataFrame(audit_rows)
    audit_df.to_csv(OUT / "PHCC_hcpcs_audit.csv", index=False)
    print(f"   PHCC_hcpcs_audit.csv: {len(audit_df)} issues")

    range_df = pd.DataFrame(range_audit_rows)
    range_df.to_csv(OUT / "PHCC_hcpcs_range_expansion_audit.csv", index=False)
    print(f"   PHCC_hcpcs_range_expansion_audit.csv: {len(range_df)} expanded rows")

    # ── K0 ARTIFACT for manual review ──
    print("\n[Artifact] Generating K0 correction artifact …")
    k0_rows = []
    for scanned, (corrected, confidence, note) in OCR_CORRECTIONS.items():
        k0_rows.append({
            "scanned_value": scanned,
            "corrected_to": corrected,
            "confidence": confidence,
            "description_match_note": note,
            "manual_verified": "",  # blank for reviewer to fill in ✓/✗
        })
    k0_df = pd.DataFrame(k0_rows)
    k0_df.to_csv(OUT / "PHCC_K0_artifact_review.csv", index=False)
    print(f"   PHCC_K0_artifact_review.csv: {len(k0_df)} corrections to review")

    # ── Summary ──
    all_clean = pd.concat([or_contr, or_part, wa_part], ignore_index=True)
    valid_count = all_clean["hcpcs_is_valid"].sum()
    total_count = len(all_clean)
    print(f"\n{'=' * 60}")
    print(f"DONE — Total cleaned rows: {total_count}")
    print(f"  Valid HCPCS:   {valid_count} ({100*valid_count/total_count:.1f}%)")
    print(f"  Invalid HCPCS: {total_count - valid_count}")
    print(f"  Ranges expanded: {len(range_df)} individual codes from ranges")
    print(f"  OCR corrections: {len([a for a in audit_rows if 'OCR' in a.get('issue_type','')])}")
    print(f"\nAll output in: {OUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
