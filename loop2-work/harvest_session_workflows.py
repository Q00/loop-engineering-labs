#!/usr/bin/env python3
"""Extract repeated workflow candidates from Codex session JSONL files.

The command is read-only. It emits a compact JSON summary and never changes
the session logs.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


DEFAULT_ROOTS = (
    Path("/Users/jaegyu.lee/.codex/sessions"),
    Path("/Users/jaegyu.lee/.codex/archived_sessions"),
)
DEFAULT_CWD = "/Users/jaegyu.lee/Project/loop-engineering-labs"

ACTION_PATTERNS = (
    ("metrics", re.compile(r"metrics\.jsonl|p95_ms|err_rate_pct|max_by", re.I)),
    ("app_log", re.compile(r"app\.log.*(?:ERROR|deploy|rollback)|rg -n -i ['\"]ERROR", re.I)),
    ("deployments", re.compile(r"deploys\.log", re.I)),
    ("draft", re.compile(r"draft\.md|postmortem", re.I)),
    ("verify", re.compile(r"검증|verify|PASS|gate|nl -ba .*draft\.md", re.I)),
    ("skill_install", re.compile(r"install-skill|\.codex/skills|codex-skills|skill-installer", re.I)),
    ("workflow_design", re.compile(r"workflow|dream|워크플로", re.I)),
)


def matching_project_session(path: Path, cwd: str) -> bool:
    try:
        for raw in path.open(encoding="utf-8"):
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if row.get("type") == "session_meta":
                return (row.get("payload") or {}).get("cwd") == cwd
    except (OSError, UnicodeDecodeError):
        return False
    return False


def extract(path: Path) -> dict:
    counts = Counter()
    ordered = []
    nested_tools = Counter()
    for raw in path.open(encoding="utf-8"):
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        payload = row.get("payload") or {}
        if row.get("type") != "response_item" or payload.get("type") != "custom_tool_call":
            continue
        text = str(payload.get("input") or "")
        for tool in ("exec_command", "apply_patch", "wait", "update_plan"):
            nested_tools[tool] += text.count(f"tools.{tool}")
        action = next((name for name, pattern in ACTION_PATTERNS if pattern.search(text)), None)
        if action:
            counts[action] += 1
            if not ordered or ordered[-1] != action:
                ordered.append(action)

    return {
        "session": path.name,
        "tool_calls": dict(nested_tools),
        "action_counts": dict(counts),
        "ordered_actions": ordered,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, default=None)
    parser.add_argument("--cwd", default=DEFAULT_CWD)
    parser.add_argument("--min-sessions", type=int, default=2)
    args = parser.parse_args()

    roots = tuple(args.root) if args.root else DEFAULT_ROOTS
    paths = sorted({path for root in roots for path in root.rglob("*.jsonl")})
    sessions = [extract(path) for path in paths if matching_project_session(path, args.cwd)]

    presence = Counter()
    for session in sessions:
        presence.update(session["action_counts"].keys())

    candidates = []
    for action, session_count in presence.items():
        if session_count >= args.min_sessions:
            candidates.append(
                {
                    "action": action,
                    "sessions": session_count,
                    "rate": round(session_count / len(sessions), 3) if sessions else 0,
                }
            )
    candidates.sort(key=lambda item: (-item["sessions"], item["action"]))

    print(json.dumps({
        "cwd": args.cwd,
        "session_count": len(sessions),
        "sessions": sessions,
        "repeated_candidates": candidates,
        "promotion_rule": {
            "min_distinct_sessions": args.min_sessions,
            "min_ordered_actions": 3,
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
