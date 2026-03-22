#!/usr/bin/env python3
"""Cohort snapshot: re-score all cities and diff against previous.
Usage: python scripts/maintenance/cohort_snapshot.py [--city city_id]
"""
import argparse, json, os, subprocess, sys
from datetime import datetime
import pandas as pd, yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

def load_cities(city_filter=None):
    with open("config/cities.yml", "r") as f:
        cities = [c for c in yaml.safe_load(f).get("cities", []) if c.get("status") == "live"]
    return [c for c in cities if c["id"] == city_filter] if city_filter else cities

def find_previous(city_id):
    for d in ["data/scored", "data/baselines"]:
        if not os.path.exists(d): continue
        cands = sorted([f for f in os.listdir(d) if f.startswith(city_id) and f.endswith(".csv") and "snapshot" not in f], reverse=True)
        if cands: return os.path.join(d, cands[0])
    return ""

def diff_scored(old_path, new_path, config):
    old_df, new_df = pd.read_csv(old_path, low_memory=False), pd.read_csv(new_path, low_memory=False)
    result = {"old_count": len(old_df), "new_count": len(new_df), "count_delta": len(new_df) - len(old_df)}
    for label, df in [("old", old_df), ("new", new_df)]:
        sc = "Composite_Score" if "Composite_Score" in df.columns else "composite_score"
        if sc in df.columns:
            s = pd.to_numeric(df[sc], errors="coerce")
            result[f"{label}_score_range"] = f"{s.min():.1f}-{s.max():.1f}"
    return result

def snapshot_city(city):
    city_id, config_path = city["id"], city.get("config", f"config/{city_id}.yml")
    result = {"city_id": city_id, "city_name": city["name"], "timestamp": datetime.utcnow().isoformat(), "status": "skipped"}
    if not os.path.exists(config_path):
        result["error"] = f"Config not found"; return result
    with open(config_path) as f: config = yaml.safe_load(f)
    prev = find_previous(city_id)
    if not prev: result["status"] = "no_baseline"; return result
    new_path = f"data/scored/{city_id}_snapshot_{datetime.utcnow().strftime('%Y-%m-%d')}.csv"
    try:
        proc = subprocess.run([sys.executable, "scripts/score/score_city.py", "--config", config_path, "--output", new_path],
                              capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            result["status"] = "score_error"; result["error"] = proc.stderr[-500:]; return result
    except Exception as e:
        result["status"] = "error"; result["error"] = str(e); return result
    if os.path.exists(new_path):
        result["diff"] = diff_scored(prev, new_path, config); result["status"] = "complete"
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", help="Single city ID")
    args = parser.parse_args()
    print(f"=== DeltaScanner Cohort Snapshot ===\nDate: {datetime.utcnow().strftime('%Y-%m-%d')}\n")
    results = []
    for city in load_cities(args.city):
        print(f"  {city['name']}...", end=" ")
        r = snapshot_city(city); results.append(r); print(r["status"])
        if "diff" in r: d = r["diff"]; print(f"    {d['old_count']} -> {d['new_count']} ({d['count_delta']:+d})")
    path = f"data/diff/cohort_diff_{datetime.utcnow().strftime('%Y-%m-%d')}.json"
    os.makedirs("data/diff", exist_ok=True)
    with open(path, "w") as f: json.dump(results, f, indent=2)
    print(f"\nReport: {path}")

if __name__ == "__main__": main()
