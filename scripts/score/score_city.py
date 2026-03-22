#!/usr/bin/env python3
"""Universal scorer for DeltaScanner.

Reads a city YAML config and produces a scored CSV.

Usage:
    python scripts/score/score_city.py --config config/miami_dade.yml --output data/scored/miami_dade_scored.csv
    python scripts/score/score_city.py --config config/miami_dade.yml --dry-run  # join key check only
"""

import argparse
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts.utils.schema import load_config
from scripts.score.normalize import get_normalizer, NORMALIZATION_FUNCTIONS
from scripts.utils.join import get_normalizer as get_join_normalizer


def load_source_data(source_config: dict) -> pd.DataFrame:
    """Load source data from path(s). Handles single path, multiple paths, or None."""
    if source_config is None:
        return pd.DataFrame()

    paths = source_config.get("paths", [])
    if not paths:
        path = source_config.get("path", "")
        if path:
            paths = [path]

    if not paths:
        return pd.DataFrame()

    frames = []
    for p in paths:
        if not os.path.exists(p):
            print(f"  WARNING: Source file not found: {p}")
            continue
        ext = os.path.splitext(p)[1].lower()
        if ext == ".xlsx":
            df = pd.read_excel(p, dtype=str)
        elif ext == ".csv":
            df = pd.read_csv(p, dtype=str, low_memory=False)
        else:
            df = pd.read_csv(p, dtype=str, low_memory=False)
        frames.append(df)
        print(f"  Loaded {len(df)} rows from {p}")

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def normalize_join_keys(df: pd.DataFrame, key_config: dict) -> pd.DataFrame:
    """Apply join key normalization to a dataframe."""
    field = key_config.get("field", "")
    norm_name = key_config.get("normalize")

    if not field or field not in df.columns:
        # Try case-insensitive match
        matches = [c for c in df.columns if c.lower() == field.lower()]
        if matches:
            field = matches[0]
        else:
            print(f"  WARNING: Join key field '{field}' not found in columns: {list(df.columns)[:10]}")
            df["_join_key"] = ""
            return df

    if norm_name and norm_name != "null":
        normalizer = get_join_normalizer(norm_name)
        if normalizer:
            df["_join_key"] = df[field].apply(normalizer)
        else:
            df["_join_key"] = df[field].astype(str).str.strip()
    else:
        df["_join_key"] = df[field].astype(str).str.strip()

    return df


def print_join_key_samples(df: pd.DataFrame, source_name: str, n: int = 5):
    """Print sample join keys for compatibility check."""
    samples = df["_join_key"].dropna().head(n).tolist()
    print(f"  {source_name} join key samples: {samples}")


def compute_derived_fields(tax_df: pd.DataFrame, ce_df: pd.DataFrame,
                           tax_fields: dict, ce_fields: dict,
                           config: dict) -> pd.DataFrame:
    """Compute derived fields and aggregate per parcel."""
    scoring = config.get("scoring", {})
    method = scoring.get("method", "intersection")
    current_year = datetime.now().year

    # --- Aggregate tax data per parcel ---
    tax_agg = pd.DataFrame()
    if not tax_df.empty and "_join_key" in tax_df.columns:
        tax_grouped = tax_df.groupby("_join_key")

        # Total delinquent balance
        balance_field = tax_fields.get("balance", "")
        if balance_field and balance_field in tax_df.columns:
            tax_df["_balance"] = pd.to_numeric(tax_df[balance_field], errors="coerce").fillna(0)
            tax_agg["total_delinquent_balance"] = tax_df.groupby("_join_key")["_balance"].sum()
        else:
            tax_agg["total_delinquent_balance"] = 0

        # Years delinquent
        yrs_field = tax_fields.get("years_delinquent", "")
        tax_year_field = tax_fields.get("tax_year", "")
        if yrs_field and yrs_field in tax_df.columns:
            tax_df["_years"] = pd.to_numeric(tax_df[yrs_field], errors="coerce").fillna(0)
            tax_agg["years_delinquent"] = tax_df.groupby("_join_key")["_years"].max()
        elif tax_year_field and tax_year_field in tax_df.columns:
            tax_df["_tax_yr"] = pd.to_numeric(tax_df[tax_year_field], errors="coerce").fillna(current_year)
            earliest = tax_df.groupby("_join_key")["_tax_yr"].min()
            tax_agg["years_delinquent"] = current_year - earliest
        else:
            tax_agg["years_delinquent"] = 1

        # Owner, address from first record
        for col_key in ["owner_name", "situs_address", "owner_address", "owner_address_1"]:
            src_col = tax_fields.get(col_key, "")
            if src_col and src_col in tax_df.columns:
                tax_agg[col_key] = tax_df.groupby("_join_key")[src_col].first()

        tax_agg = tax_agg.reset_index().rename(columns={"_join_key": "join_key"})

    # --- Aggregate CE data per parcel ---
    ce_agg = pd.DataFrame()
    if not ce_df.empty and "_join_key" in ce_df.columns:
        status_field = ce_fields.get("status", "")
        whitelist = ce_fields.get("status_whitelist", [])
        date_field = ce_fields.get("date", "")

        # Active violations count
        if status_field and status_field in ce_df.columns and whitelist:
            ce_df["_is_active"] = ce_df[status_field].isin(whitelist)
            ce_agg["active_violations"] = ce_df.groupby("_join_key")["_is_active"].sum()
        else:
            # No status filter, count all
            ce_agg["active_violations"] = ce_df.groupby("_join_key").size()

        # Total violations
        ce_agg["total_violations"] = ce_df.groupby("_join_key").size()

        # Most recent violation date
        if date_field and date_field in ce_df.columns:
            ce_df["_viol_date"] = pd.to_datetime(ce_df[date_field], errors="coerce")
            ce_agg["most_recent_violation_date"] = (
                ce_df.groupby("_join_key")["_viol_date"].max().dt.strftime("%Y-%m-%d")
            )

        # Enforcement stage (Orlando-style tiered scoring)
        stage_tiers = ce_fields.get("enforcement_stage_tiers") or \
                      config.get("sources", {}).get("ce", {}).get("enforcement_stage_tiers")
        if stage_tiers:
            status_col = status_field if status_field in ce_df.columns else None
            if status_col:
                ce_df["_stage_score"] = ce_df[status_col].map(stage_tiers).fillna(0)
                ce_agg["max_enforcement_stage"] = ce_df.groupby("_join_key")["_stage_score"].max()

        # Severity tiers (Fort Worth style)
        severity_tiers = ce_fields.get("severity_tiers") or \
                         config.get("sources", {}).get("ce", {}).get("severity_tiers")
        if severity_tiers:
            case_type_field = ce_fields.get("case_type", "")
            if case_type_field and case_type_field in ce_df.columns:
                default_sev = severity_tiers.get("default", 30)
                ce_df["_severity"] = ce_df[case_type_field].map(
                    {k: v for k, v in severity_tiers.items() if k != "default"}
                ).fillna(default_sev)
                ce_agg["max_severity"] = ce_df.groupby("_join_key")["_severity"].max()

        # CE address (for address-based joins where CE provides address)
        addr_field = ce_fields.get("address", "")
        if addr_field and addr_field in ce_df.columns:
            ce_agg["_ce_address"] = ce_df.groupby("_join_key")[addr_field].first()

        ce_agg = ce_agg.reset_index().rename(columns={"_join_key": "join_key"})

    # --- Join ---
    if method == "ce_only":
        # CE-only model: use CE as primary
        merged = ce_agg.copy()
        if not tax_agg.empty:
            merged = merged.merge(tax_agg, on="join_key", how="left", suffixes=("", "_tax"))
    elif method == "intersection":
        # Intersection: INNER JOIN on join_key
        if tax_agg.empty or ce_agg.empty:
            print("ERROR: Intersection scoring requires both tax and CE data.")
            return pd.DataFrame()
        merged = tax_agg.merge(ce_agg, on="join_key", how="inner", suffixes=("", "_ce"))
        print(f"  Intersection join: {len(merged)} parcels (tax: {len(tax_agg)}, CE: {len(ce_agg)})")

        # Join rate check
        join_rate = len(merged) / max(len(tax_agg), len(ce_agg)) * 100
        if join_rate < 5:
            print(f"  FATAL: Join match rate {join_rate:.1f}% < 5%. Something is wrong.")
            sys.exit(1)
        elif join_rate < 20:
            print(f"  WARNING: Join match rate {join_rate:.1f}% — low. Flag for Jeff review.")
    else:
        print(f"ERROR: Unknown scoring method '{method}'. Must be 'intersection' or 'ce_only'.")
        return pd.DataFrame()

    return merged


def score_parcels(merged: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Apply scoring weights and normalization to produce composite scores."""
    scoring = config.get("scoring", {})
    components = scoring.get("components", [])

    for comp in components:
        name = comp["name"]
        source_field = comp["source_field"]
        weight = comp["weight"]
        norm_type = comp["normalization"]

        # Get source data
        if source_field in merged.columns:
            raw = merged[source_field]
        else:
            print(f"  WARNING: Source field '{source_field}' not found. Using zeros.")
            raw = pd.Series(0, index=merged.index)

        # Normalize
        normalizer = get_normalizer(norm_type)
        normalized = normalizer(raw)
        col_name = f"score_{name}"
        merged[col_name] = normalized

    # Composite score: sum(weight * normalized) * 100
    composite = pd.Series(0.0, index=merged.index)
    for comp in components:
        col_name = f"score_{comp['name']}"
        composite += comp["weight"] * merged[col_name]
    merged["Composite_Score"] = (composite * 100).round(1)

    # Apply modifiers
    modifiers = scoring.get("modifiers", [])
    for mod in modifiers:
        effect = mod.get("effect", "")
        value = mod.get("value", 1.0)
        condition = mod.get("condition", "")
        # Simple condition parsing
        if "==" in condition:
            parts = condition.split("==")
            field = parts[0].strip()
            target = parts[1].strip().strip("'\"")
            if field in merged.columns:
                mask = merged[field].astype(str).str.strip() == target
            else:
                mask = pd.Series(False, index=merged.index)
        else:
            mask = pd.Series(True, index=merged.index)

        if effect == "score_multiplier":
            merged.loc[mask, "Composite_Score"] *= value
        elif effect == "score_additive":
            merged.loc[mask, "Composite_Score"] += value
        elif effect == "component_multiplier":
            target_comp = mod.get("target_component", "")
            col = f"score_{target_comp}"
            if col in merged.columns:
                merged.loc[mask, col] *= value

    # Cap at 100
    merged["Composite_Score"] = merged["Composite_Score"].clip(0, 100).round(1)

    # Rank
    merged["Rank"] = merged["Composite_Score"].rank(ascending=False, method="min").astype(int)

    # Score version
    merged["Score_Version"] = config.get("score_version", "unknown")

    return merged


def build_output(merged: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Build the output DataFrame in standard column order."""
    scoring = config.get("scoring", {})
    components = scoring.get("components", [])

    # Map available columns to standard names
    col_map = {
        "join_key": config.get("city_id", "Parcel_ID") + "_key",
        "owner_name": "Owner_Name",
        "situs_address": "Address",
        "owner_address": "Owner_Mailing_Address",
        "owner_address_1": "Owner_Mailing_Address",
        "total_delinquent_balance": "Total_Delinquent_Balance",
        "years_delinquent": "Years_Delinquent",
        "active_violations": "Active_Violations",
        "total_violations": "Total_Violations",
        "most_recent_violation_date": "Most_Recent_Violation_Date",
    }

    output = pd.DataFrame()
    output["Rank"] = merged["Rank"]
    output["Composite_Score"] = merged["Composite_Score"]
    output["Score_Version"] = merged["Score_Version"]

    # Standard fields
    for src, dst in col_map.items():
        if src in merged.columns:
            output[dst] = merged[src]

    # Ensure required columns exist (fill with empty if missing)
    for col in ["Address", "Zip", "Owner_Name", "Owner_Mailing_Address",
                "Absentee_Owner", "Property_Type", "Assessed_Value",
                "Year_Built", "Square_Footage",
                "Total_Delinquent_Balance", "Years_Delinquent",
                "Active_Violations", "Total_Violations",
                "Most_Recent_Violation_Date"]:
        if col not in output.columns:
            output[col] = ""

    # Absentee owner derivation
    if "Address" in output.columns and "Owner_Mailing_Address" in output.columns:
        addr_norm = output["Address"].astype(str).str.upper().str.strip().str[:30]
        mail_norm = output["Owner_Mailing_Address"].astype(str).str.upper().str.strip().str[:30]
        output["Absentee_Owner"] = (addr_norm != mail_norm) & (mail_norm != "") & (mail_norm != "NAN")

    # Score component columns
    for comp in components:
        col = f"score_{comp['name']}"
        if col in merged.columns:
            output[col] = merged[col].round(4)

    # Sort by rank
    output = output.sort_values("Rank").reset_index(drop=True)

    # Ensure zip codes are strings
    if "Zip" in output.columns:
        output["Zip"] = output["Zip"].astype(str).str.replace(r"\.0$", "", regex=True)

    return output


def main():
    parser = argparse.ArgumentParser(description="DeltaScanner Universal Scorer")
    parser.add_argument("--config", required=True, help="Path to city YAML config")
    parser.add_argument("--output", help="Output CSV path")
    parser.add_argument("--dry-run", action="store_true", help="Join key check only")
    args = parser.parse_args()

    print(f"=== DeltaScanner Universal Scorer ===")
    print(f"Config: {args.config}")

    # 1. Load config
    config = load_config(args.config)
    city_id = config["city_id"]
    print(f"City: {config['city_name']} ({city_id})")
    print(f"Score version: {config['score_version']}")
    print(f"Method: {config['scoring']['method']}")

    sources = config.get("sources", {})

    # 2. Load source data
    print("\nLoading tax data...")
    tax_config = sources.get("tax")
    tax_df = load_source_data(tax_config)
    tax_fields = tax_config.get("fields", {}) if tax_config else {}

    print("Loading CE data...")
    ce_config = sources.get("ce")
    ce_df = load_source_data(ce_config)
    ce_fields = ce_config.get("fields", {}) if ce_config else {}
    # Include enforcement/severity tiers from config
    if ce_config:
        for tier_key in ["enforcement_stage_tiers", "severity_tiers"]:
            if tier_key in ce_config:
                ce_fields[tier_key] = ce_config[tier_key]

    # 3. Normalize join keys
    if not tax_df.empty and tax_config:
        tax_df = normalize_join_keys(tax_df, tax_config.get("join_key", {}))
        print_join_key_samples(tax_df, "Tax")

    if not ce_df.empty and ce_config:
        ce_df = normalize_join_keys(ce_df, ce_config.get("join_key", {}))
        print_join_key_samples(ce_df, "CE")

    if args.dry_run:
        print("\n--- DRY RUN: Join key samples printed above. No scoring performed. ---")
        return

    # 4. Compute derived fields and join
    print("\nComputing derived fields and joining...")
    merged = compute_derived_fields(tax_df, ce_df, tax_fields, ce_fields, config)
    if merged.empty:
        print("ERROR: No parcels after join. Check join keys.")
        sys.exit(1)

    # Check expected range
    expected = config.get("output", {}).get("expected_parcel_range", [0, float("inf")])
    if len(merged) > expected[1] * 1.5:
        print(f"ERROR: {len(merged)} parcels exceeds expected max {expected[1]} by >50%.")
        print("Likely union instead of intersection. Halting.")
        sys.exit(1)

    # 5. Score
    print(f"\nScoring {len(merged)} parcels...")
    scored = score_parcels(merged, config)

    # 6. Build output
    output = build_output(scored, config)
    print(f"\nOutput: {len(output)} rows, {len(output.columns)} columns")
    print(f"Score range: {output['Composite_Score'].min()} - {output['Composite_Score'].max()}")

    # 7. Write
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        output.to_csv(args.output, index=False)
        print(f"Written to {args.output}")
    else:
        default_path = f"data/scored/{city_id}_scored_{datetime.now().strftime('%Y-%m-%d')}.csv"
        os.makedirs("data/scored", exist_ok=True)
        output.to_csv(default_path, index=False)
        print(f"Written to {default_path}")


if __name__ == "__main__":
    main()
