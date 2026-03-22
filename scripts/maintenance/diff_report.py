#!/usr/bin/env python3
"""Human-readable diff summary. Includes S4: web CSV sync checklist."""
import json, sys
from datetime import datetime

def format_report(diff_path):
    results = json.load(open(diff_path))
    lines = ["=" * 60, "DELTASCANNER COHORT SNAPSHOT REPORT",
             f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", "=" * 60, ""]
    sync = [r for r in results if r.get("status") == "complete" and r.get("diff", {}).get("count_delta", 0) != 0]
    if sync:
        lines.append("WEB CSV SYNC REQUIRED:")
        for r in sync: lines.append(f"  - {r['city_name']} (scored {r.get('timestamp','')[:10]})")
        lines.append("")
    for r in results:
        lines.append(f"--- {r['city_name']} ---")
        lines.append(f"  Status: {r['status']}")
        if "diff" in r:
            d = r["diff"]; lines.append(f"  Parcels: {d['old_count']} -> {d['new_count']} ({d['count_delta']:+d})")
        elif "error" in r: lines.append(f"  Error: {r['error'][:200]}")
        lines.append("")
    return "\n".join(lines)

if __name__ == "__main__":
    if len(sys.argv) < 2: print("Usage: diff_report.py <file.json>"); sys.exit(1)
    print(format_report(sys.argv[1]))
