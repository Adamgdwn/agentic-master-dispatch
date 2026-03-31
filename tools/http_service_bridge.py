#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.request


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: tools/http_service_bridge.py <action> <payload-json>")
        return 1
    bridge_url = os.environ.get("GENSPARK_BRIDGE_URL")
    bridge_token = os.environ.get("GENSPARK_BRIDGE_TOKEN")
    if not bridge_url or not bridge_token:
        print("GENSPARK_BRIDGE_URL and GENSPARK_BRIDGE_TOKEN must be set")
        return 1
    payload = {
        "action": sys.argv[1],
        "payload": json.loads(sys.argv[2]),
    }
    request = urllib.request.Request(
        bridge_url.rstrip("/") + "/invoke",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {bridge_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        print(response.read().decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
