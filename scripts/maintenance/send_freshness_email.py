#!/usr/bin/env python3
"""Send freshness check notification. Replaces inline python -c in workflow.

Exit code is always 0 — email failure should not fail the workflow.
The freshness report artifact is the primary output; email is best-effort.
"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.maintenance.notify import send_notification

def main():
    if len(sys.argv) < 2:
        print("Usage: send_freshness_email.py <report.json>"); return
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"Not found: {path}"); return
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
    send_notification(f"DeltaScanner Freshness Check - {total} flags - {date}", "\n".join(lines))
    # Always exit 0 — email is best-effort, not a gate

if __name__ == "__main__": main()
