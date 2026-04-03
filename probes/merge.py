#!/usr/bin/env python3
"""Merge probe artifacts into data/ directory.

Called by the publish job after downloading artifacts from parallel probe jobs.
Reads probe result files from artifacts/probe-*/*.json, copies them into
data/latest/, appends summaries to data/history/YYYY-MM-DD.json, and updates
data/index.json.

Usage:
    python -m probes.merge
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def find_artifact_files(artifacts_dir):
    """Find all probe JSON files in downloaded artifact directories.

    actions/download-artifact@v4 with pattern creates:
      artifacts/probe-github-us/github-us.json
      artifacts/probe-russia-firstvds/russia-firstvds.json
    """
    return sorted(artifacts_dir.glob("probe-*/*.json"))


def build_summary(result):
    """Build a history summary from a full probe result."""
    direct = result.get("direct", {})
    dc_ok = sum(1 for r in direct.values() if r.get("status") == "ok")

    summary = {
        "timestamp": result["timestamp"],
        "probe_id": result["probe_id"],
        "region": result["region"],
        "direct_ok": dc_ok,
        "direct_total": len(direct),
    }

    for p in result.get("proxy", []):
        key = f"proxy_{p['transport'].replace('-', '_')}_ok"
        summary[key] = p["get_me"]

    return summary


def merge():
    """Merge artifacts into data/ and update history + index."""
    repo_root = Path(__file__).resolve().parent.parent
    artifacts_dir = repo_root / "artifacts"
    data_dir = repo_root / "data"
    latest_dir = data_dir / "latest"
    history_dir = data_dir / "history"

    latest_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)

    # Collect history entries grouped by date
    history_by_date = defaultdict(list)
    existing_keys = defaultdict(set)

    artifact_files = find_artifact_files(artifacts_dir)
    if not artifact_files:
        print("No artifact files found in artifacts/")

    merged_count = 0
    index_set = set()

    # Load existing index
    index_file = data_dir / "index.json"
    if index_file.exists():
        index_set = set(json.loads(index_file.read_text()))

    for artifact_file in artifact_files:
        print(f"Processing {artifact_file}")
        result = json.loads(artifact_file.read_text())
        probe_id = result["probe_id"]

        # Copy to data/latest/
        dest = latest_dir / f"{probe_id}.json"
        dest.write_text(json.dumps(result, indent=2) + "\n")
        print(f"  -> {dest}")

        # Derive date from the probe's own timestamp
        ts = datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
        date_str = ts.strftime("%Y-%m-%d")

        # Load existing history for this date (once per date)
        if date_str not in history_by_date:
            history_file = history_dir / f"{date_str}.json"
            if history_file.exists():
                history_by_date[date_str] = json.loads(history_file.read_text())
            existing_keys[date_str] = {
                (e["probe_id"], e["timestamp"])
                for e in history_by_date[date_str]
            }

        # Append to history (deduped)
        summary = build_summary(result)
        key = (summary["probe_id"], summary["timestamp"])
        if key not in existing_keys[date_str]:
            history_by_date[date_str].append(summary)
            existing_keys[date_str].add(key)
            merged_count += 1
            print(f"  -> appended to history ({date_str})")
        else:
            print(f"  -> already in history, skipping")

        index_set.add(probe_id)

    # Write all modified history files
    for date_str, entries in history_by_date.items():
        entries.sort(key=lambda e: e["timestamp"])
        history_file = history_dir / f"{date_str}.json"
        history_file.write_text(json.dumps(entries, indent=2) + "\n")
        print(f"History: {len(entries)} entries in {history_file}")

    # Write index
    index = sorted(index_set)
    index_file.write_text(json.dumps(index) + "\n")
    print(f"Index: {index}")

    print(f"Merged {merged_count} new entries from {len(artifact_files)} artifacts")


if __name__ == "__main__":
    merge()
