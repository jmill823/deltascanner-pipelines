#!/usr/bin/env python3
"""Freshness check for all live DeltaScanner city sources.

Checks: URL reachability, schema match (S2), staleness flags.
Usage: python scripts/maintenance/freshness_check.py
"""
import json, os, sys
from datetime import datetime
from io import StringIO
import pandas as pd
import requests
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

SCHEMA_CHECK_TIMEOUT = 60  # seconds (NYC Socrata is slow)


def load_cities():
    with open("config/cities.yml", "r") as f:
        return [c for c in yaml.safe_load(f).get("cities", []) if c.get("status") == "live"]


def check_url(url, timeout=30):
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True)
        return {"reachable": resp.status_code < 400, "status_code": resp.status_code}
    except requests.RequestException as e:
        return {"reachable": False, "error": str(e)}


def _detect_format(url):
    """Determine response format. Priority: extension > URL pattern.

    Fixes: Chicago tax URL (resource/*.csv) was wrongly parsed as JSON
    because /resource/ was checked before .csv extension.
    """
    url_lower = url.lower()
    # Extension takes priority
    if url_lower.endswith(".csv"):
        return "csv"
    if url_lower.endswith(".json"):
        return "json"
    # ArcGIS endpoints return JSON
    if "/arcgis/" in url_lower or "/mapserver/" in url_lower or "/featureserver/" in url_lower:
        return "json"
    # Socrata /resource/ without extension: JSON
    if "/resource/" in url_lower:
        return "json"
    return "csv"  # default


def check_schema(url, config_fields):
    """S2: Pull first 5 rows and verify expected field names present."""
    fmt = _detect_format(url)
    try:
        if fmt == "json":
            resp = requests.get(url, params={"$limit": 5}, timeout=SCHEMA_CHECK_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return {"schema_ok": False, "error": "Empty JSON response"}
            if isinstance(data, list):
                source_fields = set(data[0].keys())
            elif isinstance(data, dict) and "features" in data:
                feats = data.get("features", [])
                if not feats:
                    return {"schema_ok": False, "error": "No features in ArcGIS response"}
                source_fields = set(feats[0].get("attributes", {}).keys())
            else:
                return {"schema_ok": None, "error": f"Unexpected JSON shape: {type(data).__name__}"}
        else:
            resp = requests.get(url, params={"$limit": 5}, timeout=SCHEMA_CHECK_TIMEOUT)
            resp.raise_for_status()
            text = resp.text[:10000]
            df = pd.read_csv(StringIO(text), nrows=5)
            source_fields = set(df.columns)

        expected = {v for k, v in config_fields.items() if isinstance(v, str) and v}
        missing = expected - source_fields
        return {
            "schema_ok": len(missing) == 0,
            "missing_fields": sorted(list(missing)) if missing else [],
            "source_fields_sample": sorted(list(source_fields))[:10],
        }
    except requests.Timeout:
        return {"schema_ok": None, "error": f"Timeout ({SCHEMA_CHECK_TIMEOUT}s)"}
    except Exception as e:
        return {"schema_ok": None, "error": f"{type(e).__name__}: {str(e)[:200]}"}


def check_city(city):
    city_id = city["id"]
    config_path = city.get("config", f"config/{city_id}.yml")
    result = {"city_id": city_id, "city_name": city["name"],
              "checked_at": datetime.utcnow().isoformat(), "flags": [], "sources": {}}
    if not os.path.exists(config_path):
        result["flags"].append(f"Config not found: {config_path}")
        return result
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    for src_name in ["tax", "ce"]:
        src = config.get("sources", {}).get(src_name)
        if src is None:
            result["sources"][src_name] = {"status": "not_configured"}
            continue
        url = src.get("url", "")
        if not url:
            result["sources"][src_name] = {"status": "local_only", "path": src.get("path", "")}
            continue
        url_status = check_url(url)
        src_result = {"url": url, **url_status}
        if not url_status.get("reachable"):
            result["flags"].append(f"{src_name} source DOWN: {url}")
        fields = src.get("fields", {})
        if url_status.get("reachable") and fields:
            schema = check_schema(url, fields)
            src_result["schema"] = schema
            if schema.get("missing_fields"):
                result["flags"].append(f"{src_name} SCHEMA CHANGE: {schema['missing_fields']}")
            elif schema.get("error"):
                result["flags"].append(f"{src_name} schema check error: {schema['error']}")
        result["sources"][src_name] = src_result
    return result


def main():
    print("=== DeltaScanner Freshness Check ===")
    print(f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n")
    cities = load_cities()
    print(f"Checking {len(cities)} live cities...\n")
    results, total_flags = [], 0
    for city in cities:
        print(f"  {city['name']}...", end=" ", flush=True)
        r = check_city(city)
        results.append(r)
        if r["flags"]:
            total_flags += len(r["flags"])
            print(f"{len(r['flags'])} FLAG(S)")
            for flag in r["flags"]: print(f"    - {flag}")
        else: print("OK")
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    path = f"data/freshness_report_{date_str}.json"
    os.makedirs("data", exist_ok=True)
    with open(path, "w") as f: json.dump(results, f, indent=2)
    print(f"\nReport: {path}\nTotal flags: {total_flags}")
    return results, total_flags


if __name__ == "__main__":
    _, flags = main()
    sys.exit(1 if flags > 0 else 0)
