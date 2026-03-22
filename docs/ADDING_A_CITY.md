# Adding a New City to DeltaScanner Pipelines

## Step-by-Step

1. **Create YAML config** from template in `config/`
   - Identify data sources (tax, CE, enrichment)
   - Map field names from source data
   - Set scoring weights (tax >= 50%, min 3 components)
   - Define expected parcel range

2. **Place source data** in `data/raw/`
   - For auto-extractable sources: add URL to config
   - For PRR/manual data: place CSV/XLSX in data/raw/

3. **Run join key compatibility check**
   ```
   python scripts/score/score_city.py --config config/[city].yml --dry-run
   ```

4. **Score the city**
   ```
   python scripts/score/score_city.py --config config/[city].yml --output data/scored/[city]_scored.csv
   ```

5. **Validate output**
   ```
   python scripts/score/validate_output.py --scored data/scored/[city]_scored.csv --config config/[city].yml
   ```

6. **Normalize for web**
   ```
   python scripts/score/normalize_csv.py --input data/scored/[city]_scored.csv --output data/web-stage/[city].csv
   ```

7. **Copy to web repo**: `data/web-stage/[city].csv` -> `deltascanner/public/data/[city].csv`

8. **Update registry**: Add city entry to `config/cities.yml`

9. **Add Deal Flow tab**: Use the dealflow-sheet-spec skill
