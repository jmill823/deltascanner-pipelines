#!/usr/bin/env python3
"""Direct CSV/XLSX HTTP download extractor for DeltaScanner.

Handles:
- Direct CSV downloads
- XLSX to CSV conversion
- Fixed-width format parsing (for TX TRW files)
"""

import os

import pandas as pd
import requests


def download_csv(url: str, output_path: str, **kwargs) -> pd.DataFrame:
    """Download a CSV file from a URL."""
    print(f"  Downloading from {url}...")
    resp = requests.get(url, timeout=120, stream=True)
    resp.raise_for_status()

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    df = pd.read_csv(output_path, dtype=str, low_memory=False)
    print(f"  Downloaded: {len(df)} rows, {len(df.columns)} columns")
    return df


def download_xlsx(url: str, output_path: str, sheet_name: int = 0,
                  header_row: int = 0) -> pd.DataFrame:
    """Download and convert XLSX to CSV."""
    print(f"  Downloading XLSX from {url}...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    xlsx_path = output_path.replace(".csv", ".xlsx")
    os.makedirs(os.path.dirname(xlsx_path) or ".", exist_ok=True)
    with open(xlsx_path, "wb") as f:
        f.write(resp.content)

    df = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=header_row, dtype=str)
    df.to_csv(output_path, index=False)
    print(f"  Converted: {len(df)} rows, {len(df.columns)} columns")
    return df


def load_local_csv(path: str) -> pd.DataFrame:
    """Load a local CSV file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Source file not found: {path}")
    df = pd.read_csv(path, dtype=str, low_memory=False)
    print(f"  Loaded: {len(df)} rows from {path}")
    return df


def load_local_xlsx(path: str, sheet_name: int = 0,
                    header_row: int = 0) -> pd.DataFrame:
    """Load a local XLSX file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Source file not found: {path}")
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row, dtype=str)
    print(f"  Loaded: {len(df)} rows from {path}")
    return df


def parse_fixed_width(path: str, output_path: str,
                      col_specs: dict, line_length: int = None,
                      encoding: str = "latin-1") -> pd.DataFrame:
    """Parse fixed-width file using column position specs.

    Args:
        path: Input fixed-width file
        output_path: Output CSV path
        col_specs: Dict of {col_name: "start:end"} position strings
        line_length: Expected line length (for validation)
        encoding: File encoding

    Returns:
        DataFrame
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Source file not found: {path}")

    positions = {}
    for name, spec in col_specs.items():
        start, end = spec.split(":")
        positions[name] = (int(start), int(end))

    rows = []
    with open(path, "r", encoding=encoding) as f:
        for i, line in enumerate(f):
            if line_length and len(line.rstrip("\n\r")) != line_length:
                continue
            row = {}
            for name, (start, end) in positions.items():
                row[name] = line[start:end].strip()
            rows.append(row)

            if (i + 1) % 100000 == 0:
                print(f"  Parsed {i + 1} lines...")

    df = pd.DataFrame(rows)
    print(f"  Parsed: {len(df)} rows from {path}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df.to_csv(output_path, index=False)
    return df
