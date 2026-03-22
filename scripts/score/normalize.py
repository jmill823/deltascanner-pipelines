"""Shared normalization functions for DeltaScanner scoring.

Only two normalization methods are permitted:
- log_normalize: log1p(value) / log1p(max_value) -> 0-1
- minmax_normalize: (value - min) / (max - min) -> 0-1

There is NO recency function. This is intentional and non-negotiable.
"""

import numpy as np
import pandas as pd


def log_normalize(series: pd.Series) -> pd.Series:
    """Log-normalized 0-1: log1p(value) / log1p(max_value)."""
    series = pd.to_numeric(series, errors="coerce").fillna(0).clip(lower=0)
    max_val = series.max()
    if max_val == 0:
        return pd.Series(0.0, index=series.index)
    return np.log1p(series) / np.log1p(max_val)


def minmax_normalize(series: pd.Series) -> pd.Series:
    """Min-max normalized 0-1: (value - min) / (max - min)."""
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series(0.0, index=series.index)
    return (series - min_val) / (max_val - min_val)


def binary_normalize(series: pd.Series) -> pd.Series:
    """Binary 0/1: truthy values become 1.0, falsy become 0.0."""
    return series.astype(bool).astype(float)


def linear_normalize(series: pd.Series) -> pd.Series:
    """Linear pass-through: assumes values already in 0-1 (or 0-100) range.
    Clips to 0-1."""
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    max_val = series.max()
    if max_val > 1:
        return (series / max_val).clip(0, 1)
    return series.clip(0, 1)


def ordinal_normalize(series: pd.Series, mapping: dict = None) -> pd.Series:
    """Ordinal normalization: maps discrete values to 0-1 scale.
    Default mapping for years_delinquent: 1->0.25, 2->0.50, 3->0.75, 4+->1.0"""
    if mapping is None:
        mapping = {1: 0.25, 2: 0.50, 3: 0.75}
    series = pd.to_numeric(series, errors="coerce").fillna(0).astype(int)
    result = series.map(mapping)
    # Anything >= max key gets 1.0
    max_key = max(mapping.keys())
    result = result.where(result.notna(), np.where(series >= max_key, 1.0, 0.0))
    return result.astype(float)


def tiered_normalize(series: pd.Series) -> pd.Series:
    """Tiered normalization: assumes values are 0-100 tier scores.
    Divides by 100 to get 0-1."""
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    return (series / 100.0).clip(0, 1)


NORMALIZATION_FUNCTIONS = {
    "log": log_normalize,
    "minmax": minmax_normalize,
    "binary": binary_normalize,
    "linear": linear_normalize,
    "ordinal": ordinal_normalize,
    "tiered": tiered_normalize,
}


def get_normalizer(name: str):
    """Get normalization function by name. Raises ValueError for unknown types.
    Rejects any recency-based normalization."""
    forbidden = ["recency", "inverse_days", "freshness"]
    if name.lower() in forbidden:
        raise ValueError(
            f"Normalization type '{name}' is prohibited. "
            "Freshness-based recency is counter-predictive and banned."
        )
    if name not in NORMALIZATION_FUNCTIONS:
        raise ValueError(
            f"Unknown normalization type '{name}'. "
            f"Valid types: {list(NORMALIZATION_FUNCTIONS.keys())}"
        )
    return NORMALIZATION_FUNCTIONS[name]
