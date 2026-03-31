from __future__ import annotations

import argparse
import os

from .desktop import run_desktop_app
from .server import run_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Governed Agent Lab.")
    parser.add_argument("--mode", choices=["desktop", "server"], default=os.environ.get("GOVERNED_AGENT_LAB_MODE", "desktop"))
    parser.add_argument("--host", default=os.environ.get("GOVERNED_AGENT_LAB_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("GOVERNED_AGENT_LAB_PORT", "8000")))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "server":
        run_server(host=args.host, port=args.port)
        return
    run_desktop_app(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
