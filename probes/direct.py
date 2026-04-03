"""Direct TCP connectivity probe for Telegram DCs.

Tests whether Telegram datacenter IPs are reachable on port 443.
A failure here means Telegram is blocked at the network level.
"""

import socket
import time

from probes.targets import DC_PORT, PRODUCTION_DCS


def probe_direct():
    """Probe TCP connectivity to all production Telegram DCs.

    Returns:
        Dict mapping DC label to result dict with status/latency_ms/error.
    """
    results = {}
    for dc_id, addrs in PRODUCTION_DCS.items():
        label = f"dc{dc_id}"
        ip = addrs["ipv4"]
        start = time.monotonic()
        try:
            s = socket.create_connection((ip, DC_PORT), timeout=5)
            s.close()
            elapsed = (time.monotonic() - start) * 1000
            results[label] = {"status": "ok", "latency_ms": round(elapsed)}
        except OSError as e:
            elapsed = (time.monotonic() - start) * 1000
            results[label] = {
                "status": "fail",
                "latency_ms": round(elapsed),
                "error": str(e),
            }
    return results
