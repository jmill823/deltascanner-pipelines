#!/usr/bin/env python3
"""Web CSV normalizer for DeltaScanner.

Produces web-ready CSVs for the Vercel-deployed frontend.
Enforces enrichment preservation: if a previous web CSV exists,
merges enrichment columns from it into the new output.

Usage:
    python scripts/score/normalize_csv.py --input data/scored/city_scored.csv --output data/web-stage/city.csv
"""

import argparse
import os
import sys

import pandas as pd


def normalize_for_web(input_path: str, output_path: str):
    """Normalize a scored CSV for the web frontend."""
    df = pd.read_csv(input_path, low_memory=False)
    print(f"Input: {len(df)} rows, {len(df.columns)} columns from {input_path}")

    # Enrichment Preservation Rule:
    # If previous web CSV exists, merge enrichment columns from it
    if os.path.exists(output_path):
        prev = pd.read_csv(output_path, low_memory=False)
        prev_cols = set(prev.columns)
        new_cols = set(df.columns)
        enrichment_cols = prev_cols - new_cols

        if enrichment_cols:
            print(f"  Preserving {len(enrichment_cols)} enrichment columns from previous: {enrichment_cols}")
            # Find common join column (Rank or address)
            join_col = None
            for candidate in ["Address", "Rank", "join_key"]:
                if candidate in prev.columns and candidate in df.columns:
                    join_col = candidate
                    break
            if join_col:
                enrich_df = prev[[join_col] + list(enrichment_cols)].drop_duplicates(subset=[join_col])
                df = df.merge(enrich_df, on=join_col, how="left")
                print(f"  Merged on '{join_col}': {len(df)} rows, {len(df.columns)} columns")

        if len(df.columns) < len(prev.columns):
            print(f"  WARNING: Column count decreased ({len(prev.columns)} -> {len(df.columns)})")

    # Clean up
    # Ensure Zip is string
    if "Zip" in df.columns:
        df["Zip"] = df["Zip"].astype(str).str.replace(r"\.0$", "", regex=True)

    # Sort by Rank
    if "Rank" in df.columns:
        df = df.sort_values("Rank")

    # Remove internal columns
    drop_cols = [c for c in df.columns if c.startswith("_")]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Output: {len(df)} rows, {len(df.columns)} columns to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="DeltaScanner Web CSV Normalizer")
    parser.add_argument("--input", required=True, help="Scored CSV path")
    parser.add_argument("--output", required=True, help="Web-stage CSV path")
    args = parser.parse_args()

    normalize_for_web(args.input, args.output)


if __name__ == "__main__":
    main()
