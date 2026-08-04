#!/usr/bin/env python3
"""Append one observable Codex work-call event to the local lab trace."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("usage: record_tool_call.py LOG TOOL PURPOSE TARGET")
    path, tool, purpose, target = sys.argv[1:]
    event = {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "tool": tool,
        "purpose": purpose,
        "target": target,
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
