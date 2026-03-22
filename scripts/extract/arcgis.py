#!/usr/bin/env python3
"""ArcGIS FeatureServer REST extractor for DeltaScanner.

Paginated download from ArcGIS REST endpoints with automatic
maxRecordCount detection and epoch timestamp conversion.
"""

import os
import time
from datetime import datetime

import pandas as pd
import requests


def extract_arcgis(url: str, output_path: str,
                   where_clause: str = "1=1",
                   out_fields: str = "*",
                   token: str = None) -> pd.DataFrame:
    """Download data from an ArcGIS FeatureServer REST endpoint.

    Args:
        url: ArcGIS endpoint (e.g., .../MapServer/0)
        output_path: Where to save the CSV
        where_clause: SQL where filter (default: all records)
        out_fields: Comma-separated field list (default: all)
        token: Optional ArcGIS token

    Returns:
        DataFrame with all downloaded data
    """
    # Get maxRecordCount from server metadata
    meta_params = {"f": "json"}
    if token:
        meta_params["token"] = token
    meta_resp = requests.get(url, params=meta_params, timeout=30)
    meta_resp.raise_for_status()
    meta = meta_resp.json()
    max_records = meta.get("maxRecordCount", 1000)
    print(f"  Server maxRecordCount: {max_records}")

    # Identify date fields for epoch conversion
    date_fields = set()
    for field in meta.get("fields", []):
        if field.get("type") == "esriFieldTypeDate":
            date_fields.add(field["name"])

    all_features = []
    offset = 0

    while True:
        params = {
            "where": where_clause,
            "outFields": out_fields,
            "resultOffset": offset,
            "resultRecordCount": max_records,
            "f": "json",
        }
        if token:
            params["token"] = token

        query_url = f"{url}/query"
        print(f"  Fetching offset {offset}...")
        resp = requests.get(query_url, params=params, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        if not features:
            break

        rows = [f["attributes"] for f in features]
        all_features.extend(rows)
        print(f"  Got {len(features)} features (total: {len(all_features)})")

        if len(features) < max_records:
            break
        offset += max_records
        time.sleep(0.5)

    df = pd.DataFrame(all_features)

    # Convert epoch milliseconds to ISO dates
    for col in date_fields:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit="ms", errors="coerce").dt.strftime("%Y-%m-%d")

    print(f"  Total: {len(df)} rows, {len(df.columns)} columns")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"  Saved to {output_path}")

    return df
