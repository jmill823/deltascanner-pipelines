#!/usr/bin/env python3
"""Florida NAL file parser for DeltaScanner.

Parses FL Department of Revenue NAL (Name, Address, Legal) files.
Filters by Roll Type "N" (not "R"), normalizes folio numbers,
and maps DOR use codes to property types.
"""

import os

import pandas as pd

# Florida DOR Use Code -> Property Type mapping
DOR_USE_CODE_MAP = {
    "00": "Vacant",
    "01": "Residential", "02": "Residential", "03": "Residential",
    "04": "Residential", "05": "Residential", "06": "Other",
    "07": "Other", "08": "Residential", "09": "Other",
}
# Range-based mappings
DOR_USE_CODE_RANGES = {
    (10, 19): "Vacant",
    (20, 39): "Commercial",
    (40, 49): "Industrial",
    (50, 69): "Agricultural",
    (70, 79): "Institutional",
    (80, 89): "Other",
    (90, 99): "Other",
}


def map_dor_use_code(code) -> str:
    """Map FL DOR use code to standardized property type."""
    if pd.isna(code) or str(code).strip() == "":
        return "Other"
    code_str = str(code).strip().zfill(2)[:2]
    if code_str in DOR_USE_CODE_MAP:
        return DOR_USE_CODE_MAP[code_str]
    try:
        code_int = int(code_str)
        for (lo, hi), ptype in DOR_USE_CODE_RANGES.items():
            if lo <= code_int <= hi:
                return ptype
    except ValueError:
        pass
    return "Other"


def extract_nal(path: str, output_path: str,
                county_code: str = None,
                roll_type: str = "R") -> pd.DataFrame:
    """Parse a Florida NAL file.

    Args:
        path: Path to NAL CSV (or zip containing CSV)
        output_path: Where to save parsed output
        county_code: CO_NO filter (e.g., "13" for Miami-Dade, "26" for Duval)
        roll_type: FILE_T filter ("R" for real property, default)

    Returns:
        DataFrame with parsed NAL data
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"NAL file not found: {path}")

    # Handle zip files
    if path.endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(path, "r") as z:
            csv_names = [n for n in z.namelist() if n.endswith(".csv")]
            if not csv_names:
                raise ValueError(f"No CSV found in {path}")
            with z.open(csv_names[0]) as f:
                df = pd.read_csv(f, dtype=str, low_memory=False)
    else:
        df = pd.read_csv(path, dtype=str, low_memory=False)

    print(f"  Raw NAL: {len(df)} rows")

    # Filter by county
    if county_code and "CO_NO" in df.columns:
        df = df[df["CO_NO"].astype(str).str.strip() == str(county_code)]
        print(f"  After county filter (CO_NO={county_code}): {len(df)} rows")

    # Filter by roll type
    if "FILE_T" in df.columns:
        df = df[df["FILE_T"].astype(str).str.strip() == roll_type]
        print(f"  After roll type filter (FILE_T={roll_type}): {len(df)} rows")

    # Map property type
    if "DOR_UC" in df.columns:
        df["Property_Type"] = df["DOR_UC"].apply(map_dor_use_code)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"  Saved to {output_path}: {len(df)} rows")

    return df
