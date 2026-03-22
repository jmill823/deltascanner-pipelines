# deltascanner-pipelines

DeltaScanner data pipelines: extraction, scoring, validation, and automation for distressed property intelligence.

## Architecture

Two-repo model:
- **deltascanner** (web) — React frontend, deployed via Vercel
- **deltascanner-pipelines** (this repo) — Data pipelines, scoring, cron jobs

## Quick Start

```bash
pip install -r requirements.txt
python scripts/score/score_city.py --config config/miami_dade.yml --output data/scored/miami_dade_scored.csv
python scripts/score/validate_output.py --scored data/scored/miami_dade_scored.csv --config config/miami_dade.yml
```

## Structure

- `config/` — Per-city YAML scoring configs + master registry
- `scripts/score/` — Universal scorer, validator, normalizer
- `scripts/extract/` — Source data extractors (Socrata, ArcGIS, CSV, NAL)
- `scripts/maintenance/` — Freshness checks, cohort snapshots
- `data/` — Raw, scored, web-stage, archive, baselines
- `tests/` — Pytest suite
- `docs/` — Scoring standard, city patterns, adding a city guide
