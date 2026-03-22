#!/usr/bin/env python3
"""Send cohort snapshot notification. Replaces inline python -c in workflow."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.maintenance.diff_report import format_report
from scripts.maintenance.notify import send_notification

def main():
    if len(sys.argv) < 2:
        print("Usage: send_cohort_email.py <diff.json>"); sys.exit(1)
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"Not found: {path}"); sys.exit(1)
    with open(path) as f:
        results = json.load(f)
    n = sum(1 for r in results if r.get("status") == "complete")
    date = results[0].get("timestamp", "")[:10] if results else "unknown"
    ok = send_notification(f"DeltaScanner Cohort Snapshot - {n} cities refreshed - {date}", format_report(path))
    sys.exit(0 if ok else 1)

if __name__ == "__main__": main()
