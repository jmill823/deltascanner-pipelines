"""Schema validation utilities for DeltaScanner scoring configs."""

import yaml
import sys

# Standard output column order
STANDARD_COLUMNS = [
    "Rank", "Composite_Score", "Score_Version", "Address", "Zip",
    # Join key name varies per city
    "Owner_Name", "Owner_Mailing_Address", "Absentee_Owner",
    "Property_Type", "Assessed_Value", "Year_Built", "Square_Footage",
    "Total_Delinquent_Balance", "Years_Delinquent",
    "Active_Violations", "Total_Violations", "Most_Recent_Violation_Date",
    # Score components follow (dynamic, named score_<component>)
]


def load_config(config_path: str) -> dict:
    """Load and validate a city YAML config."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    validate_config(config)
    return config


def validate_config(config: dict):
    """Validate scoring config against rules.

    Rules enforced:
    1. Weights must sum to 1.0 (within tolerance)
    2. Tax weight >= 0.50 (unless ce_only: true)
    3. Minimum 3 components (unless ce_only: true with < 3 available)
    4. No recency normalization types
    5. Scoring method must be 'intersection' or 'ce_only'
    """
    errors = []

    scoring = config.get("scoring", {})
    components = scoring.get("components", [])
    method = scoring.get("method", "intersection")
    is_ce_only = config.get("ce_only", False)

    # Method check
    if method not in ("intersection", "ce_only"):
        errors.append(
            f"Scoring method '{method}' is invalid. Must be 'intersection' or 'ce_only'."
        )

    # Weight sum check
    weights = [c.get("weight", 0) for c in components]
    weight_sum = sum(weights)
    if abs(weight_sum - 1.0) > 0.01:
        errors.append(
            f"Component weights sum to {weight_sum:.3f}, must be 1.0."
        )

    # Component count check
    if len(components) < 3:
        if not is_ce_only:
            errors.append(
                f"Only {len(components)} scoring components. Minimum 3 required."
            )
        # CE-only cities with < 3 get a warning, not error
        elif len(components) < 2:
            errors.append(
                f"Only {len(components)} scoring components. Even CE-only needs at least 2."
            )

    # Tax weight check (skip for ce_only)
    if not is_ce_only:
        # Determine which components are tax-related
        tax_keywords = [
            "delinquency", "delinq", "lien", "tax", "balance", "duration",
            "deed", "recurrence",
        ]
        tax_weight = 0.0
        for c in components:
            name = c.get("name", "").lower()
            if any(kw in name for kw in tax_keywords):
                tax_weight += c.get("weight", 0)
        if tax_weight < 0.50:
            errors.append(
                f"Tax weight is {tax_weight:.2f}, must be >= 0.50."
            )

    # Recency check
    forbidden_norms = ["recency", "inverse_days", "freshness"]
    for c in components:
        norm = c.get("normalization", "")
        if norm.lower() in forbidden_norms:
            errors.append(
                f"Component '{c.get('name')}' uses forbidden normalization '{norm}'. "
                "Freshness-based recency is prohibited."
            )

    if errors:
        city = config.get("city_id", "unknown")
        msg = f"Config validation failed for {city}:\n"
        msg += "\n".join(f"  - {e}" for e in errors)
        raise ValueError(msg)

    return True
