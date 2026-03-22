# DeltaScanner — Scoring Standard

Canonical scoring rules. Mirrors CLAUDE.md scoring section.

## Non-Negotiable Rules

1. **Intersection-only scoring.** A parcel MUST have at least one CE record AND at least one tax delinquency record to receive a score.
2. **No freshness-based recency.** Duration (years delinquent) is correct. Recency (days since last activity) is prohibited.
3. **Tax weight >= 50%.** Financial distress signals must account for at least 50% of the composite score.
4. **Minimum 3 score components.** Two-component models are too brittle.
5. **Scores are within-city rankings only.** No cross-city comparability.

## Template Weights (Miami v2)

- 50% delinquency duration (min-max 0-1)
- 35% delinquency amount (log-normalized 0-1)
- 15% active violations (log-normalized 0-1)

## Normalization Methods

- **Log-normalized 0-1:** `log1p(value) / log1p(max_value)`
- **Min-max 0-1:** `(value - min) / (max - min)`
- Dollar amounts: raw integers
- Dates: ISO format strings
- Zip codes: strings (never floats)
