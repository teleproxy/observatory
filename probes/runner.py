#!/usr/bin/env python3
"""Observatory probe runner.

Runs direct DC reachability and proxy E2E probes, writes results to
data/latest/{probe_id}.json and appends a summary to
data/history/YYYY-MM-DD.json.

Usage:
    PROXY_HOST=... PROXY_PORT=... PROXY_SECRET=... \
    TG_BOT_TOKEN=... \
    python -m probes.runner --probe-id github-us --region "US (GitHub Actions)"
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from probes.direct import probe_direct


def run(probe_id, region):
    """Run all probes and write results."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"[{timestamp}] probe_id={probe_id} region={region}")

    # Direct DC reachability
    print("Running direct DC probe...")
    direct_results = probe_direct()
    dc_ok = sum(1 for r in direct_results.values() if r["status"] == "ok")
    dc_total = len(direct_results)
    print(f"  Direct: {dc_ok}/{dc_total} DCs reachable")

    # Proxy E2E (skip if required env vars are missing)
    proxy_results = []
    required_vars = ["PROXY_HOST", "PROXY_PORT", "PROXY_SECRET", "TG_BOT_TOKEN"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(f"  Proxy E2E: SKIPPED (missing: {', '.join(missing)})")
    else:
        print("Running proxy E2E probe...")
        try:
            from probes.proxy_e2e import probe_proxy
            proxy_results = probe_proxy()
            for r in proxy_results:
                status = "OK" if r["get_me"] else "FAIL"
                detail = r.get("error") or f"{r['total_ms']}ms"
                print(f"  {r['transport']}: {status} ({detail})")
        except Exception as e:
            print(f"  Proxy E2E: ERROR ({type(e).__name__}: {e})")
            proxy_results = [{
                "transport": "obfs2",
                "connected": False,
                "authenticated": False,
                "get_me": False,
                "error": f"{type(e).__name__}: {e}",
            }]

    # Build result
    result = {
        "timestamp": timestamp,
        "probe_id": probe_id,
        "region": region,
        "direct": direct_results,
    }
    if proxy_results:
        result["proxy"] = proxy_results

    # Write latest
    data_dir = Path(__file__).resolve().parent.parent / "data"
    latest_dir = data_dir / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)

    latest_file = latest_dir / f"{probe_id}.json"
    latest_file.write_text(json.dumps(result, indent=2) + "\n")
    print(f"  Wrote {latest_file}")

    # Append to daily history
    history_dir = data_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "timestamp": timestamp,
        "probe_id": probe_id,
        "region": region,
        "direct_ok": dc_ok,
        "direct_total": dc_total,
    }
    for r in proxy_results:
        key = f"proxy_{r['transport'].replace('-', '_')}_ok"
        summary[key] = r["get_me"]

    history_file = history_dir / f"{date_str}.json"
    if history_file.exists():
        history = json.loads(history_file.read_text())
    else:
        history = []
    history.append(summary)
    history_file.write_text(json.dumps(history, indent=2) + "\n")
    print(f"  Appended to {history_file}")

    # Update probe index (list of known probe IDs)
    index_file = data_dir / "index.json"
    if index_file.exists():
        index = json.loads(index_file.read_text())
    else:
        index = []
    if probe_id not in index:
        index.append(probe_id)
        index.sort()
        index_file.write_text(json.dumps(index) + "\n")
        print(f"  Updated {index_file}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Observatory probe runner")
    parser.add_argument("--probe-id", required=True, help="Unique probe identifier")
    parser.add_argument("--region", required=True, help="Human-readable region name")
    args = parser.parse_args()

    result = run(args.probe_id, args.region)

    # Exit with error if both direct and proxy failed
    direct_ok = any(
        r["status"] == "ok" for r in result["direct"].values()
    )
    proxy_ok = any(r["get_me"] for r in result.get("proxy", [{"get_me": True}]))

    if not direct_ok and not proxy_ok:
        print("\nBOTH direct and proxy probes failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
