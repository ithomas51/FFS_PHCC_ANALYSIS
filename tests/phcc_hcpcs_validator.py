#!/usr/bin/env python3
"""
PHCC HCPCS validator and profiling utility.

Purpose
-------
Validate PHCC fee schedule CSVs, detect HCPCS issues, profile modifier usage, and
classify rate note patterns before the full fee schedule comparison pipeline is built.

Default behavior
----------------
If no input paths are supplied, the script searches the current working directory for:
    PHCC_*.csv

Outputs
-------
Creates an output directory (default: ./phcc_validation_output) containing:
- phcc_column_detection.csv
- phcc_hcpcs_validation_summary.csv
- phcc_hcpcs_validation_issues.csv
- phcc_modifier_profile.csv
- phcc_rate_note_profile.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

VALID_HCPCS_RE = re.compile(r"^[A-Z][0-9]{4}$")


@dataclass(frozen=True)
class FileSchema:
    path: Path
    hcpcs_col: str
    modifier_col: str | None
    rate_cols: tuple[str, ...]


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).replace("\xa0", " ").strip()


def compact_hcpcs(value: object) -> str:
    return re.sub(r"\s+", "", normalize_text(value).upper())


def normalize_code_token(token: str) -> str | None:
    token = re.sub(r"[^A-Z0-9O]", "", token.upper())
    if len(token) != 5:
        return None
    if not token[0].isalpha():
        return None
    tail = token[1:].replace("O", "0")
    if not tail.isdigit():
        return None
    return token[0] + tail


def canonicalize_modifier(value: object) -> tuple[str, str, str]:
    """
    Returns:
        raw_cleaned,
        token_pipe_key,
        primary_modifier

    Notes:
    - strips asterisks
    - splits on slash, comma, and whitespace
    - preserves order while removing duplicates
    """
    raw = normalize_text(value).upper()
    cleaned = raw.replace("*", "")
    tokens = [t for t in re.split(r"[/,\s]+", cleaned) if t]
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    key = "|".join(ordered)
    primary = ordered[0] if ordered else ""
    return cleaned, key, primary


def classify_rate_value(value: object) -> tuple[str, str]:
    text = normalize_text(value)
    if not text:
        return "BLANK", ""
    probe = text.replace("$", "").replace(",", "").replace("\n", " ").strip()
    try:
        float(probe)
        return "NUMERIC", probe
    except ValueError:
        pass

    low = probe.lower()
    if "retail less" in low:
        return "RETAIL_LESS_PCT", probe
    if "non-billable" in low:
        return "NON_BILLABLE", probe
    if "quote" in low:
        return "QUOTE", probe
    if "per 15 min" in low:
        return "PER_15_MIN_NOTE", probe
    if "medicare allowable less" in low:
        return "MEDICARE_ALLOWABLE_LESS_PCT", probe
    return "OTHER_NOTE", probe


def expand_range_count(range_text: str) -> int | None:
    try:
        start, end = range_text.split("-", 1)
        if start[0] != end[0]:
            return None
        return int(end[1:]) - int(start[1:]) + 1
    except Exception:
        return None


def analyze_hcpcs(raw_value: object) -> dict[str, object]:
    raw = normalize_text(raw_value)
    compact = compact_hcpcs(raw)
    if not raw:
        return {
            "status": "INVALID",
            "issue_type": "blank",
            "hcpcs_compact": compact,
            "suggested_hcpcs": "",
            "range_start": "",
            "range_end": "",
            "range_expand_count": "",
            "auto_recoverable": False,
        }

    if VALID_HCPCS_RE.fullmatch(compact):
        return {
            "status": "VALID",
            "issue_type": "valid_exact_or_whitespace",
            "hcpcs_compact": compact,
            "suggested_hcpcs": compact,
            "range_start": "",
            "range_end": "",
            "range_expand_count": "",
            "auto_recoverable": True,
        }

    if "?" in compact:
        return {
            "status": "INVALID",
            "issue_type": "question_mark",
            "hcpcs_compact": compact,
            "suggested_hcpcs": "",
            "range_start": "",
            "range_end": "",
            "range_expand_count": "",
            "auto_recoverable": False,
        }

    slim = re.sub(r"[^A-Z0-9O\-]", "", raw.upper())

    # Range detection first
    range_match = re.match(r"^([A-Z])\-*([0-9O]{4})\-+([A-Z])?\-*([0-9O]{4})$", slim)
    if range_match:
        prefix1, digits1, prefix2, digits2 = range_match.groups()
        prefix2 = prefix2 or prefix1
        start = normalize_code_token(prefix1 + digits1)
        end = normalize_code_token(prefix2 + digits2)
        suggestion = f"{start}-{end}" if start and end else ""
        return {
            "status": "RANGE",
            "issue_type": "range_expandable",
            "hcpcs_compact": compact,
            "suggested_hcpcs": suggestion,
            "range_start": start or "",
            "range_end": end or "",
            "range_expand_count": expand_range_count(suggestion) if suggestion else "",
            "auto_recoverable": bool(suggestion),
        }

    # Single-code recovery with hyphen / OCR cleanup
    single_match = re.match(r"^([A-Z])\-*([0-9O]{4})\-*$", slim)
    if single_match:
        prefix, digits = single_match.groups()
        suggestion = normalize_code_token(prefix + digits) or ""
        issue_type = "ocr_o_vs_zero" if "O" in digits else "hyphen_noise"
        return {
            "status": "RECOVERABLE" if suggestion else "INVALID",
            "issue_type": issue_type,
            "hcpcs_compact": compact,
            "suggested_hcpcs": suggestion,
            "range_start": "",
            "range_end": "",
            "range_expand_count": "",
            "auto_recoverable": bool(suggestion),
        }

    # Leading code followed by extra text, e.g. "A7000\nSuction"
    leading_match = re.match(r"^\s*([A-Z][0-9O]{4})\b", raw.upper().replace("\n", " "))
    if leading_match:
        suggestion = normalize_code_token(leading_match.group(1)) or ""
        return {
            "status": "RECOVERABLE" if suggestion else "INVALID",
            "issue_type": "extra_text_after_code",
            "hcpcs_compact": compact,
            "suggested_hcpcs": suggestion,
            "range_start": "",
            "range_end": "",
            "range_expand_count": "",
            "auto_recoverable": bool(suggestion),
        }

    return {
        "status": "INVALID",
        "issue_type": "unrecognized",
        "hcpcs_compact": compact,
        "suggested_hcpcs": "",
        "range_start": "",
        "range_end": "",
        "range_expand_count": "",
        "auto_recoverable": False,
    }


def detect_schema(path: Path) -> FileSchema:
    df = pd.read_csv(path, dtype=str)
    cols = list(df.columns)

    hcpcs_col = "HCPCS" if "HCPCS" in cols else None
    if not hcpcs_col:
        raise ValueError(f"{path.name}: expected HCPCS column not found. Columns={cols!r}")

    modifier_col = None
    for candidate in ("Modifier", "Mod"):
        if candidate in cols:
            modifier_col = candidate
            break

    rate_cols = tuple(c for c in cols if "Rate" in c)
    return FileSchema(path=path, hcpcs_col=hcpcs_col, modifier_col=modifier_col, rate_cols=rate_cols)


def resolve_inputs(inputs: Iterable[str]) -> list[Path]:
    explicit = [Path(p) for p in inputs]
    if explicit:
        return explicit
    return sorted(Path(".").glob("PHCC_*.csv"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PHCC HCPCS columns and profile modifier/rate patterns.")
    parser.add_argument("inputs", nargs="*", help="PHCC CSV files. If omitted, script searches for PHCC_*.csv in CWD.")
    parser.add_argument(
        "--output-dir",
        default="phcc_validation_output",
        help="Directory for CSV outputs. Default: %(default)s",
    )
    args = parser.parse_args()

    input_paths = resolve_inputs(args.inputs)
    if not input_paths:
        raise SystemExit("No PHCC input files found. Supply files explicitly or run in a directory containing PHCC_*.csv.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    column_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    issue_rows: list[dict[str, object]] = []
    modifier_rows: list[dict[str, object]] = []
    rate_note_rows: list[dict[str, object]] = []

    for path in input_paths:
        schema = detect_schema(path)
        df = pd.read_csv(path, dtype=str)

        # Column detection
        column_rows.append(
            {
                "source_file": path.name,
                "row_count": len(df),
                "column_count": len(df.columns),
                "hcpcs_col": schema.hcpcs_col,
                "modifier_col": schema.modifier_col or "",
                "rate_cols": "|".join(schema.rate_cols),
                "all_columns": "|".join(df.columns),
            }
        )

        analyses = []
        for row_number, row in enumerate(df.to_dict(orient="records"), start=2):
            hcpcs_info = analyze_hcpcs(row.get(schema.hcpcs_col))
            modifier_clean, modifier_key, modifier_primary = canonicalize_modifier(row.get(schema.modifier_col)) if schema.modifier_col else ("", "", "")
            analyses.append(hcpcs_info)

            if hcpcs_info["status"] != "VALID":
                issue_rows.append(
                    {
                        "source_file": path.name,
                        "row_number": row_number,
                        "hcpcs_raw": normalize_text(row.get(schema.hcpcs_col)),
                        "hcpcs_compact": hcpcs_info["hcpcs_compact"],
                        "status": hcpcs_info["status"],
                        "issue_type": hcpcs_info["issue_type"],
                        "suggested_hcpcs": hcpcs_info["suggested_hcpcs"],
                        "range_start": hcpcs_info["range_start"],
                        "range_end": hcpcs_info["range_end"],
                        "range_expand_count": hcpcs_info["range_expand_count"],
                        "auto_recoverable": hcpcs_info["auto_recoverable"],
                        "modifier_raw": normalize_text(row.get(schema.modifier_col)) if schema.modifier_col else "",
                        "modifier_cleaned": modifier_clean,
                        "modifier_key": modifier_key,
                        "modifier_primary": modifier_primary,
                        "description": normalize_text(row.get("Description")),
                    }
                )

        analysis_df = pd.DataFrame(analyses)
        issue_counts = analysis_df["issue_type"].value_counts().to_dict()
        status_counts = analysis_df["status"].value_counts().to_dict()

        summary_rows.append(
            {
                "source_file": path.name,
                "rows_total": len(df),
                "valid_rows": int(status_counts.get("VALID", 0)),
                "recoverable_single_code_rows": int(status_counts.get("RECOVERABLE", 0)),
                "range_rows": int(status_counts.get("RANGE", 0)),
                "invalid_manual_review_rows": int(status_counts.get("INVALID", 0)),
                "valid_or_recoverable_pct": round(
                    ((status_counts.get("VALID", 0) + status_counts.get("RECOVERABLE", 0)) / len(df)) * 100, 2
                ),
                "question_mark_rows": int(issue_counts.get("question_mark", 0)),
                "ocr_o_vs_zero_rows": int(issue_counts.get("ocr_o_vs_zero", 0)),
                "hyphen_noise_rows": int(issue_counts.get("hyphen_noise", 0)),
                "range_expandable_rows": int(issue_counts.get("range_expandable", 0)),
                "extra_text_after_code_rows": int(issue_counts.get("extra_text_after_code", 0)),
                "range_expansion_total_codes": int(
                    pd.to_numeric(analysis_df.loc[analysis_df["status"] == "RANGE", "range_expand_count"], errors="coerce").fillna(0).sum()
                ),
            }
        )

        # Modifier profile
        if schema.modifier_col:
            modifier_df = df[[schema.modifier_col]].copy()
            modifier_df["modifier_raw"] = modifier_df[schema.modifier_col].map(normalize_text)
            modifier_df[["modifier_cleaned", "modifier_key", "modifier_primary"]] = modifier_df[schema.modifier_col].apply(
                lambda v: pd.Series(canonicalize_modifier(v))
            )
            mod_profile = (
                modifier_df.groupby(["modifier_raw", "modifier_cleaned", "modifier_key", "modifier_primary"], dropna=False)
                .size()
                .reset_index(name="row_count")
            )
            for rec in mod_profile.to_dict(orient="records"):
                rec["source_file"] = path.name
                modifier_rows.append(rec)

        # Rate note profile
        for rate_col in schema.rate_cols:
            prof = df[rate_col].map(classify_rate_value).apply(pd.Series)
            prof.columns = ["rate_value_type", "rate_value_detail"]
            prof_df = pd.concat([df[[rate_col]], prof], axis=1)
            prof_group = (
                prof_df.groupby(["rate_value_type", rate_col], dropna=False)
                .size()
                .reset_index(name="row_count")
                .sort_values(["rate_value_type", "row_count"], ascending=[True, False])
            )
            for rec in prof_group.to_dict(orient="records"):
                rate_note_rows.append(
                    {
                        "source_file": path.name,
                        "rate_column": rate_col,
                        "rate_value_type": rec["rate_value_type"],
                        "rate_value_raw": normalize_text(rec[rate_col]),
                        "row_count": rec["row_count"],
                    }
                )

    pd.DataFrame(column_rows).to_csv(output_dir / "phcc_column_detection.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(output_dir / "phcc_hcpcs_validation_summary.csv", index=False)
    pd.DataFrame(issue_rows).to_csv(output_dir / "phcc_hcpcs_validation_issues.csv", index=False)
    pd.DataFrame(modifier_rows).to_csv(output_dir / "phcc_modifier_profile.csv", index=False)
    pd.DataFrame(rate_note_rows).to_csv(output_dir / "phcc_rate_note_profile.csv", index=False)

    print("Created:")
    for name in [
        "phcc_column_detection.csv",
        "phcc_hcpcs_validation_summary.csv",
        "phcc_hcpcs_validation_issues.csv",
        "phcc_modifier_profile.csv",
        "phcc_rate_note_profile.csv",
    ]:
        print(f"- {output_dir / name}")

    print("\nSummary")
    for row in summary_rows:
        print(
            f"- {row['source_file']}: "
            f"valid={row['valid_rows']}, "
            f"recoverable={row['recoverable_single_code_rows']}, "
            f"ranges={row['range_rows']}, "
            f"manual_review={row['invalid_manual_review_rows']}, "
            f"range_expansion_total_codes={row['range_expansion_total_codes']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
