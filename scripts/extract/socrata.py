#!/usr/bin/env python3
"""Socrata SODA API extractor for DeltaScanner.

Handles paginated downloads from Socrata open data portals.
Supports both CSV and JSON endpoints.
"""

import os
import time

import pandas as pd
import requests


def extract_socrata(url: str, output_path: str, app_token: str = None,
                    page_size: int = 50000, max_rows: int = None,
                    where_clause: str = None) -> pd.DataFrame:
    """Download data from a Socrata SODA API endpoint.

    Args:
        url: Socrata API endpoint (e.g., https://data.cityofchicago.org/resource/22u3-xenr.json)
        output_path: Where to save the CSV
        app_token: Optional Socrata app token (env: SOCRATA_APP_TOKEN)
        page_size: Records per request
        max_rows: Max total rows (None = all)
        where_clause: Optional $where filter

    Returns:
        DataFrame with all downloaded data
    """
    if app_token is None:
        app_token = os.environ.get("SOCRATA_APP_TOKEN", "")

    all_rows = []
    offset = 0

    while True:
        params = {
            "$limit": page_size,
            "$offset": offset,
        }
        if app_token:
            params["$$app_token"] = app_token
        if where_clause:
            params["$where"] = where_clause

        print(f"  Fetching offset {offset}...")
        resp = requests.get(url, params=params, timeout=120)
        resp.raise_for_status()

        if url.endswith(".json"):
            data = resp.json()
            if not data:
                break
            all_rows.extend(data)
        else:
            # CSV endpoint
            from io import StringIO
            chunk = pd.read_csv(StringIO(resp.text), dtype=str)
            if chunk.empty:
                break
            all_rows.append(chunk)

        fetched = len(data) if url.endswith(".json") else len(chunk)
        print(f"  Got {fetched} rows (total: {offset + fetched})")

        if fetched < page_size:
            break
        offset += page_size

        if max_rows and offset >= max_rows:
            break

        time.sleep(1)  # Rate limiting

    if url.endswith(".json"):
        df = pd.DataFrame(all_rows)
    else:
        df = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()

    print(f"  Total: {len(df)} rows, {len(df.columns)} columns")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"  Saved to {output_path}")

    return df
