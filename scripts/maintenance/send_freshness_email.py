#!/usr/bin/env python3
"""Send freshness check notification. Replaces inline python -c in workflow."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.maintenance.notify import send_notification

def main():
    if len(sys.argv) < 2:
        print("Usage: send_freshness_email.py <report.json>"); sys.exit(1)
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"Not found: {path}"); sys.exit(1)
    with open(path) as f:
        results = json.load(f)
    total = sum(len(c.get("flags", [])) for c in results)
    date = results[0]["checked_at"][:10] if results else "unknown"
    lines = [f"Checked {len(results)} cities. {total} flag(s).\n"]
    for c in results:
        if c.get("flags"):
            lines.append(f"{c['city_name']}:")
            for fl in c["flags"]: lines.append(f"  - {fl}")
            lines.append("")
    if total == 0:
        lines.append("All source URLs reachable. No schema changes detected.")
    ok = send_notification(f"DeltaScanner Freshness Check - {total} flags - {date}", "\n".join(lines))
    sys.exit(0 if ok else 1)

if __name__ == "__main__": main()
