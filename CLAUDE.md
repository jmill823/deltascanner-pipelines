# DeltaScanner Pipelines — CC Project Context

Read this at the start of every session.

## What This Repo Is

This is the **pipelines** repository for DeltaScanner — a distressed property intelligence platform. It contains all data extraction, scoring, validation, and automation code. It is SEPARATE from the web repo (`jmill823/deltascanner`) which serves the React frontend via Vercel.

13 cities live, ~240K scored parcels. Config-driven architecture: all city-specific behavior lives in YAML configs under `config/`.

## Two-Repo Model

- `jmill823/deltascanner` (web) — React frontend, `public/data/*.csv`, deployed via Vercel
- `jmill823/deltascanner-pipelines` (this repo) — Extraction, scoring, validation, cron jobs
- Data flows: extract → score → validate → normalize → `data/web-stage/` → manual copy to web repo

Do NOT modify the web repo from this repo. The copy step is intentionally manual.

## Scoring Rules (Non-Negotiable)

1. **Intersection-only scoring.** A parcel MUST have at least one CE record AND at least one tax delinquency record. Exception: `ce_only: true` cities (Philadelphia, Orlando).
2. **No freshness-based recency.** Duration (years delinquent) is allowed. Recency (days since last activity) is prohibited.
3. **Tax weight >= 50%.** Exception: `ce_only: true` cities.
4. **Minimum 3 score components.** Two-component models are too brittle.
5. **Scores are within-city rankings only.**

## Normalization Methods (Only These)

- **Log-normalized 0–1:** `log1p(value) / log1p(max_value)`
- **Min-max 0–1:** `(value - min) / (max - min)`
- Dollar amounts: raw integers
- Dates: ISO format strings
- Zip codes: strings (never floats)

## Key Commands

```bash
# Score a city
python scripts/score/score_city.py --config config/miami_dade.yml --output data/scored/miami_dade_scored.csv

# Dry run (join key check only)
python scripts/score/score_city.py --config config/miami_dade.yml --dry-run

# Validate output
python scripts/score/validate_output.py --scored data/scored/miami_dade_scored.csv --config config/miami_dade.yml

# Normalize for web
python scripts/score/normalize_csv.py --input data/scored/miami_dade_scored.csv --output data/web-stage/miami_dade.csv

# Extract source data
python scripts/extract/extract_city.py --config config/miami_dade.yml --source all

# Freshness check (all cities)
python scripts/maintenance/freshness_check.py

# Cohort snapshot (all cities or single)
python scripts/maintenance/cohort_snapshot.py
python scripts/maintenance/cohort_snapshot.py --city miami_dade

# Run tests
pytest tests/ -v
```

## Config-Driven Architecture

All city-specific behavior lives in YAML configs (`config/*.yml`). The universal scorer (`scripts/score/score_city.py`) reads the config and produces scored CSVs. Zero city-specific conditionals in Python code.

Build failure test: `if city_id == 'miami'` anywhere in Python is a build failure.

## Adding a New City

See `docs/ADDING_A_CITY.md` for step-by-step instructions.

## Join Key Compatibility Check (Mandatory)

Before writing ANY join logic, run `--dry-run` to print 5 sample values from each source. Confirm format match after normalization.

Known gotchas:
- Fort Worth (8-digit vs 11-digit account numbers)
- Dallas (address-based crosswalk through DCAD)
- Orlando (join on ALT_KEY, NOT PARCEL_ID)
- Florida NAL PARCEL_ID has trailing "R" suffix
- Palm Beach PCN is 17-digit

## Enrichment Preservation Rule

When re-scoring any city: `normalize_csv.py` merges enrichment columns from the previous web CSV. Verify column count matches or exceeds previous version.

## Output Validation Checklist (Automated)

`validate_output.py` checks:
- No field is 100% null or 100% zero
- Score distribution has reasonable spread
- Absentee_Owner is not 100% False
- Parcel count in expected range
- Property_Type is not 100% "Other"
- Zip codes are strings
- Column count matches standard schema

## GitHub Actions

- `freshness-check.yml`: Monthly 15th — checks all source URLs + schema
- `cohort-snapshot.yml`: Monthly 1st — re-scores all cities, diffs, notifies
- `test.yml`: On PR — runs pytest

Secrets needed: `SMTP_USER`, `SMTP_PASS`, `NOTIFY_EMAIL`

## File Locations

- City configs: `config/*.yml`
- Master registry: `config/cities.yml`
- Scorer: `scripts/score/score_city.py`
- Extractors: `scripts/extract/`
- Maintenance: `scripts/maintenance/`
- Tests: `tests/`
- Scored CSVs: `data/scored/` (gitignored)
- Web-stage CSVs: `data/web-stage/` (gitignored)
- Raw data: `data/raw/` (gitignored)
- Tracked: `data/archive/`, `data/diff/`, `data/baselines/`, `data/experiments/`

## What NOT to Do

- Do not modify the web repo from here
- Do not build union scoring
- Do not use freshness-based recency
- Do not add city-specific conditionals to Python code
- Do not overwrite enriched CSVs with base scored outputs
- Do not guess field names — inspect data first
- Do not skip the join key compatibility check
- Do not skip the output validation checklist

---

*DeltaScanner | Pipelines CLAUDE.md | March 21, 2026*
