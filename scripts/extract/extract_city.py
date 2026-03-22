#!/usr/bin/env python3
"""City data extraction dispatcher for DeltaScanner.

Reads a city config and extracts the specified source data.

Usage:
    python scripts/extract/extract_city.py --config config/miami_dade.yml --source tax
    python scripts/extract/extract_city.py --config config/miami_dade.yml --source ce
    python scripts/extract/extract_city.py --config config/miami_dade.yml --source enrichment
    python scripts/extract/extract_city.py --config config/miami_dade.yml --source all
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts.utils.schema import load_config
from scripts.extract.socrata import extract_socrata
from scripts.extract.arcgis import extract_arcgis
from scripts.extract.csv_download import download_csv, load_local_csv, load_local_xlsx
from scripts.extract.nal import extract_nal


def extract_source(source_config: dict, city_id: str, source_name: str):
    """Extract a single source based on its platform config."""
    if source_config is None:
        print(f"  {source_name}: null (no data source configured)")
        return None

    platform = source_config.get("platform", "")
    url = source_config.get("url", "")
    path = source_config.get("path", "")
    paths = source_config.get("paths", [])

    # Default output path
    output_path = path or f"data/raw/{city_id}_{source_name}.csv"

    print(f"  {source_name}: platform={platform}")

    if platform == "socrata" and url:
        pagination = source_config.get("pagination", {})
        page_size = pagination.get("page_size", 50000)
        filter_clause = source_config.get("filter", "")
        return extract_socrata(
            url=url, output_path=output_path,
            page_size=page_size,
            where_clause=filter_clause if filter_clause else None,
        )

    elif platform == "arcgis" and url:
        return extract_arcgis(url=url, output_path=output_path)

    elif platform == "csv_direct":
        if url:
            return download_csv(url=url, output_path=output_path)
        elif path and os.path.exists(path):
            return load_local_csv(path)
        elif paths:
            # Multiple local files
            import pandas as pd
            frames = []
            for p in paths:
                if os.path.exists(p):
                    frames.append(load_local_csv(p))
                else:
                    print(f"    WARNING: File not found: {p}")
            return pd.concat(frames, ignore_index=True) if frames else None
        else:
            print(f"    WARNING: No URL or local path for {source_name}")
            return None

    elif platform == "xlsx":
        if path and os.path.exists(path):
            return load_local_xlsx(path)
        elif url:
            from scripts.extract.csv_download import download_xlsx
            return download_xlsx(url=url, output_path=output_path)
        else:
            print(f"    WARNING: No URL or local path for {source_name}")
            return None

    elif platform == "nal":
        if path and os.path.exists(path):
            return extract_nal(path=path, output_path=output_path)
        else:
            print(f"    WARNING: NAL file not found: {path}")
            return None

    elif platform == "csv":
        # Generic local CSV
        if path and os.path.exists(path):
            return load_local_csv(path)
        return None

    else:
        print(f"    WARNING: Unknown platform '{platform}' for {source_name}")
        return None


def main():
    parser = argparse.ArgumentParser(description="DeltaScanner City Extractor")
    parser.add_argument("--config", required=True, help="Path to city YAML config")
    parser.add_argument("--source", required=True,
                        choices=["tax", "ce", "enrichment", "all"],
                        help="Which source to extract")
    args = parser.parse_args()

    config = load_config(args.config)
    city_id = config["city_id"]
    sources = config.get("sources", {})

    print(f"=== DeltaScanner Extractor: {config['city_name']} ===")

    if args.source == "all":
        for src_name in ["tax", "ce", "enrichment"]:
            print(f"\nExtracting {src_name}...")
            extract_source(sources.get(src_name), city_id, src_name)
    else:
        print(f"\nExtracting {args.source}...")
        extract_source(sources.get(args.source), city_id, args.source)

    print("\nDone.")


if __name__ == "__main__":
    main()
