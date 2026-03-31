#!/usr/bin/env python3
from __future__ import annotations

import os
import sqlite3
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: tools/sqlite_readonly.py <sql>")
        return 1
    db_path = os.environ.get("SQLITE_DB_PATH")
    if not db_path:
        print("SQLITE_DB_PATH is not set")
        return 1
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cursor = conn.execute(sys.argv[1])
        for row in cursor.fetchall():
            print(row)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
