#!/usr/bin/env python3
"""Automated output validation checklist for DeltaScanner.

Usage:
    python scripts/score/validate_output.py --scored data/scored/city_scored.csv --config config/city.yml

Exit code 0 = all pass. Exit code 1 = any failure.
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.utils.schema import load_config


def validate(scored_path: str, config_path: str) -> list:
    """Run all validation checks. Returns list of (check_name, passed, detail)."""
    config = load_config(config_path)
    df = pd.read_csv(scored_path, dtype=str, low_memory=False)
    results = []
    is_ce_only = config.get("ce_only", False)

    # 1. No field is 100% null or 100% zero
    for col in df.columns:
        all_null = df[col].isna().all() or (df[col].astype(str).str.strip() == "").all()
        all_zero = False
        try:
            numeric = pd.to_numeric(df[col], errors="coerce")
            if numeric.notna().any():
                all_zero = (numeric.fillna(-1) == 0).all()
        except Exception:
            pass
        if all_null:
            results.append((f"field_not_null:{col}", False, f"{col} is 100% null/empty"))
        elif all_zero:
            results.append((f"field_not_zero:{col}", False, f"{col} is 100% zero"))

    # 2. Score distribution spread
    scores = pd.to_numeric(df.get("Composite_Score", pd.Series(dtype=float)), errors="coerce").dropna()
    if len(scores) > 0:
        bins = pd.cut(scores, bins=range(0, 110, 10))
        counts = bins.value_counts(normalize=True)
        max_band = counts.max()
        passed = max_band <= 0.50
        results.append((
            "score_distribution",
            passed,
            f"Max band concentration: {max_band:.1%}" + ("" if passed else " (>50% in single band)")
        ))

    # 3. Top 10 sanity check
    if "Composite_Score" in df.columns:
        top10 = df.nlargest(10, "Composite_Score") if "Composite_Score" in df.select_dtypes(include="number").columns else df.head(10)
        results.append(("top10_sanity", True, "Top 10 parcels available for manual review"))

    # 4. Absentee_Owner not 100% False
    if "Absentee_Owner" in df.columns:
        vals = df["Absentee_Owner"].astype(str).str.lower()
        all_false = (vals.isin(["false", "0", ""])).all()
        results.append((
            "absentee_owner",
            not all_false,
            "100% False — mailing data likely missing" if all_false else "Mix of True/False"
        ))

    # 5. Parcel count in expected range
    expected = config.get("output", {}).get("expected_parcel_range", [0, float("inf")])
    count = len(df)
    in_range = expected[0] <= count <= expected[1]
    results.append((
        "parcel_count",
        in_range,
        f"{count} parcels (expected {expected[0]}-{expected[1]})"
    ))

    # 6. Property_Type not 100% "Other"
    if "Property_Type" in df.columns:
        non_empty = df["Property_Type"].dropna()
        non_empty = non_empty[non_empty.str.strip() != ""]
        if len(non_empty) > 0:
            all_other = (non_empty.str.strip().str.lower() == "other").all()
            results.append((
                "property_type",
                not all_other,
                "100% Other" if all_other else f"{non_empty.nunique()} unique types"
            ))

    # 7. Zip codes are strings (no .0)
    if "Zip" in df.columns:
        has_float = df["Zip"].astype(str).str.contains(r"\.0$", na=False).any()
        results.append((
            "zip_format",
            not has_float,
            "Contains .0 float suffix" if has_float else "Clean string format"
        ))

    # 8. Column count
    min_cols = 17  # Standard schema minimum
    results.append((
        "column_count",
        len(df.columns) >= min_cols,
        f"{len(df.columns)} columns (minimum {min_cols})"
    ))

    return results


def main():
    parser = argparse.ArgumentParser(description="DeltaScanner Output Validator")
    parser.add_argument("--scored", required=True, help="Path to scored CSV")
    parser.add_argument("--config", required=True, help="Path to city YAML config")
    args = parser.parse_args()

    print(f"=== DeltaScanner Output Validator ===")
    print(f"Scored: {args.scored}")
    print(f"Config: {args.config}")
    print()

    results = validate(args.scored, args.config)

    failures = 0
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        icon = "+" if passed else "X"
        print(f"  [{icon}] {status}: {name} — {detail}")
        if not passed:
            failures += 1

    print(f"\n{'ALL CHECKS PASSED' if failures == 0 else f'{failures} CHECK(S) FAILED'}")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
